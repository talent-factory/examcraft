/**
 * Client-seitiges Melden von Frontend-Fehlern an den Backend-Proxy-Endpoint
 * `POST /api/v1/monitoring/client-errors` (TF-864, ADR-012-Pattern, TF-866).
 *
 * Bewusst LOKAL reimplementiert statt `@talent-factory/specula-client`
 * (specula-client-js) zu importieren, obwohl dessen `createErrorReporter`/
 * `ErrorBoundary`-Helper genau diese Aufgabe schon loesen: `core/frontend`
 * wird unveraendert als Open-Source-Mirror veroeffentlicht (`git subtree
 * split --prefix=core`), und `bun install` laeuft dort ohne Zugriff auf
 * private GitHub-Pakete (`specula-client-js` ist nicht auf npm). Anders als
 * beim Python-Pendant (Laufzeit-`ImportError`, "package-fail-open", siehe
 * `core/backend/config/observability.py`, TF-865) gibt es fuer einen
 * Bundler kein Aequivalent: ein statischer `import` aus einem nicht
 * aufloesbaren Paket bricht den gesamten Build, nicht nur eine einzelne
 * Funktion. Diese Datei bildet daher nur die hier benoetigte API-Form von
 * specula-client-js' `errorReporting.ts` nach — genau das gleiche Vorgehen
 * wie `core/backend/api/monitoring.py`s `_sanitize_url()`/
 * `_strip_control_chars()`, die aus demselben Grund lokal statt importiert
 * sind (siehe dessen Moduldoc).
 *
 * Der Endpoint ist BEWUSST unauthentifiziert erreichbar (muss auch fuer
 * nicht eingeloggte User funktionieren, z. B. Fehler auf der Login-Seite) —
 * deshalb kein `httpClient.postJson()`: das haengt einen
 * `Authorization`-Header an, loest bei 401 einen Token-Refresh/Force-Logout
 * aus und wirft bei einer Non-2xx-Antwort. Ein Report-Fehlschlag darf die
 * App nie beeintraechtigen (ADR-012): `reportError` wirft nie, bleibt aber
 * ueber `console.error`/`console.warn` sichtbar statt lautlos zu
 * verschwinden.
 */

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const ENDPOINT = `${API_BASE_URL}/api/v1/monitoring/client-errors`;
const DEFAULT_MAX_REPORTS = 5;

/**
 * Gilt fuer ALLE Reporting-Pfade dieses Moduls — nicht nur fuer die globalen
 * `window`-Handler aus {@link initErrorReporting}, sondern auch fuer
 * {@link reportClientError}/{@link reportHandledError} (genutzt von
 * `ErrorBoundary` und den Handled-Error-Call-Sites). Paritaet zum bisherigen
 * `initSentry()`, das laut eigener Doku nur "in staging and production
 * environments" lief: `REACT_APP_ENABLE_SENTRY` ist per `.env.example`
 * lokal `false`, wodurch `Sentry.init()` nie lief und jeder
 * `Sentry.captureException()`/`Sentry.ErrorBoundary`-Aufruf ein dokumentiertes
 * No-op ohne Netzwerk-Call war. Ohne dieses Gate wuerde jeder lokal
 * gefangene Fehler einen echten `fetch()` gegen `REACT_APP_API_URL`
 * ausloesen (z. B. gegen eine geteilte Staging-Instanz, falls lokal darauf
 * gezeigt wird) — und in Tests, die dieses Modul nicht mocken (z. B.
 * `HelpOnboarding.test.tsx`), unnoetiges `console.error`-Rauschen erzeugen.
 *
 * Bewusst live pro Aufruf ausgewertet (nicht einmalig beim Modul-Load
 * gecacht wie {@link ENDPOINT}), damit Tests `REACT_APP_ENVIRONMENT` ohne
 * Modul-Reset umschalten koennen.
 */
function isReportingEnabled(): boolean {
  return (process.env.REACT_APP_ENVIRONMENT || 'development') !== 'development';
}

export interface ClientErrorPayload {
  /** Fehlermeldung (`Error.message`). */
  message: string;
  /** Stacktrace (`Error.stack ?? ''`). */
  stack: string;
  /** Roh-URL der Seite, auf der der Fehler auftrat. Wird intern via
   * {@link safeUrl} sanitized, bevor sie den Endpoint erreicht. */
  url: string;
  /** `navigator.userAgent` im Zeitpunkt des Fehlers. */
  userAgent: string;
  /** React-Component-Stack (`ErrorInfo.componentStack`), nur bei ueber
   * `ErrorBoundary#componentDidCatch` gefangenen Render-Fehlern gesetzt. */
  componentStack?: string;
}

export interface ErrorReporterOptions {
  /** Pfad oder vollqualifizierte URL des `/client-errors`-Proxy-Endpoints. */
  endpoint: string;
  /**
   * Obergrenze an Reports ueber die Lebensdauer dieser Reporter-Instanz
   * (Default 5). Schuetzt vor Self-DoS: ein sich wiederholender
   * Frontend-Fehler (z. B. ein fehlerhafter `setInterval`) darf nicht
   * unbegrenzt gegen den Backend-Proxy und dessen Rate-Limit feuern.
   */
  maxReports?: number;
}

export interface ErrorReporter {
  /** Meldet einen Fehler an den konfigurierten Endpoint. Wirft nie. */
  reportError(payload: ClientErrorPayload): Promise<void>;
  /**
   * Registriert Listener fuer `error`/`unhandledrejection` auf `window` —
   * Fehler, die nicht von React abgefangen werden (ausserhalb des
   * Render-Baums, in Event-Handlern, rejected Promises). Render-Fehler
   * faengt stattdessen `ErrorBoundary#componentDidCatch` ab.
   * @returns Cleanup-Funktion, die die Listener wieder entfernt.
   */
  attachGlobalHandlers(): () => void;
}

/**
 * Sanitized eine URL vor dem Versand an den Backend-Proxy: behaelt nur
 * Origin + Pfad, strippt Query-String und Fragment (koennen
 * Capability-Tokens tragen, z. B. `/auth/reset-password/confirm?token=...`,
 * `/verify-email?token=...`). Der Backend-Proxy saniert `payload.url`
 * zusaetzlich selbst (Defense-in-Depth, siehe `monitoring.py`), diese
 * Funktion ist die client-seitige erste Verteidigungslinie.
 */
export function safeUrl(rawUrl: string): string {
  try {
    const url = new URL(rawUrl);
    return `${url.origin}${url.pathname}`;
  } catch {
    // Kein parsbares URL-Objekt — konservativ nichts Rohes weiterreichen,
    // aber sichtbar machen, dass hier etwas verworfen wurde.
    console.warn(`[errorReporting] safeUrl() konnte "${rawUrl}" nicht parsen; url wird im Report weggelassen.`);
    return '';
  }
}

/**
 * Erzeugt eine isolierte Reporter-Instanz mit eigenem, gekapseltem
 * Drossel-/Dedup-Zustand — hilfreich vor allem fuer Tests (jeder Test kann
 * eine frische Instanz erzeugen statt sich modulweiten Zustand zu teilen).
 * Wirft sofort (statt spaeter still zu versagen), wenn `options.endpoint`
 * leer ist oder `options.maxReports` keine gueltige, nicht-negative Zahl
 * ist.
 */
export function createErrorReporter(options: ErrorReporterOptions): ErrorReporter {
  const { endpoint, maxReports = DEFAULT_MAX_REPORTS } = options;

  if (endpoint.trim() === '') {
    throw new Error('createErrorReporter: `endpoint` ist Pflicht und darf nicht leer sein.');
  }
  if (!Number.isFinite(maxReports) || maxReports < 0) {
    throw new Error(
      `createErrorReporter: \`maxReports\` muss eine nicht-negative, endliche Zahl sein, erhalten: ${String(maxReports)}.`
    );
  }

  let reportCount = 0;
  let capWarningLogged = false;
  const reportedSignatures = new Set<string>();

  function shouldReport(payload: ClientErrorPayload): boolean {
    if (reportCount >= maxReports) {
      if (!capWarningLogged) {
        capWarningLogged = true;
        console.warn(
          `[errorReporting] maxReports (${maxReports}) erreicht — weitere Client-Fehler werden nicht mehr gemeldet.`
        );
      }
      return false;
    }
    // Dedup ueber message+stack, damit derselbe wiederkehrende Fehler nicht
    // x-mal einzeln zaehlt, bevor der Deckel greift.
    const signature = JSON.stringify([payload.message, payload.stack]);
    if (reportedSignatures.has(signature)) {
      return false;
    }
    reportedSignatures.add(signature);
    reportCount += 1;
    return true;
  }

  async function reportError(payload: ClientErrorPayload): Promise<void> {
    try {
      if (!shouldReport(payload)) {
        return;
      }
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...payload, url: safeUrl(payload.url) }),
        // Reports, die kurz vor einem Seitenwechsel/Unload gefeuert werden,
        // sollen den Browser ueberleben statt gecancelt zu werden.
        keepalive: true,
      });
      // `fetch()` wirft nur bei Netzwerkfehlern, nicht bei 4xx/5xx — ohne
      // diese Pruefung verschwaende eine vom Backend abgelehnte Meldung
      // (z. B. Payload-Limits, Rate-Limit) komplett spurlos.
      if (!response.ok) {
        console.error(
          `[errorReporting] Melden fehlgeschlagen fuer "${payload.message}" (endpoint=${endpoint}): HTTP ${response.status}`
        );
      }
    } catch (err) {
      console.error(
        `[errorReporting] Melden fehlgeschlagen fuer "${payload.message}" (endpoint=${endpoint}):`,
        err
      );
    }
  }

  function attachGlobalHandlers(): () => void {
    const handleError = (event: ErrorEvent): void => {
      void reportError({
        message: event.error instanceof Error ? event.error.message : event.message,
        stack: event.error instanceof Error ? (event.error.stack ?? '') : '',
        url: window.location.href,
        userAgent: navigator.userAgent,
      });
    };

    const handleRejection = (event: PromiseRejectionEvent): void => {
      const reason = event.reason as unknown;
      void reportError({
        message: reason instanceof Error ? reason.message : String(reason),
        stack: reason instanceof Error ? (reason.stack ?? '') : '',
        url: window.location.href,
        userAgent: navigator.userAgent,
      });
    };

    // addEventListener statt window.onerror =/window.onunhandledrejection =:
    // komponiert mit ggf. bereits registrierten Handlern, statt sie
    // stillschweigend zu ersetzen.
    window.addEventListener('error', handleError);
    window.addEventListener('unhandledrejection', handleRejection);

    return () => {
      window.removeEventListener('error', handleError);
      window.removeEventListener('unhandledrejection', handleRejection);
    };
  }

  return { reportError, attachGlobalHandlers };
}

const defaultReporter = createErrorReporter({ endpoint: ENDPOINT });

/** App-weite Standard-Instanz, geteilt zwischen `ErrorBoundary` (Render-Fehler)
 * und {@link initErrorReporting} (globale Handler) — ein gemeinsamer
 * Drossel-Zustand statt zweier unabhaengiger Deckel.
 *
 * No-op in `development` (siehe {@link isReportingEnabled}) — anders als
 * `defaultReporter.reportError` selbst (bleibt fuer `createErrorReporter()`-
 * Konsumenten und Tests unbedingt, die eigene Instanzen mit vollem
 * Wurf-Budget erwarten). */
export function reportClientError(payload: ClientErrorPayload): Promise<void> {
  if (!isReportingEnabled()) {
    return Promise.resolve();
  }
  return defaultReporter.reportError(payload);
}

/**
 * Meldet einen von der Anwendung selbst gefangenen Fehler (`catch`-Block)
 * oder eine reine Warn-Nachricht (`error` als String statt `Error`) —
 * Ersatz fuer die frueheren `Sentry.captureException()`/`captureMessage()`-
 * Aufrufe ausserhalb von `ErrorBoundary`/`initErrorReporting` (TF-866).
 *
 * Der `/client-errors`-Endpoint kennt kein strukturiertes `tags`/`extra`
 * (`ClientErrorIn` in `monitoring.py` hat `extra="forbid"` und nur
 * `message`/`stack`/`url`/`userAgent`/`componentStack`) — `context` wird
 * deshalb als `key=value`-Suffix in `message` codiert statt als eigenes
 * Feld uebertragen, bleibt damit aber in derselben Log-Zeile sichtbar.
 */
export function reportHandledError(error: unknown, context: Record<string, unknown> = {}): void {
  const err = error instanceof Error ? error : new Error(String(error));
  const contextSuffix = Object.entries(context)
    .filter(([, value]) => value !== undefined)
    .map(([key, value]) => `${key}=${typeof value === 'string' ? value : JSON.stringify(value)}`)
    .join(' ');
  void reportClientError({
    message: contextSuffix ? `${err.message} [${contextSuffix}]` : err.message,
    stack: err.stack ?? '',
    url: window.location.href,
    userAgent: navigator.userAgent,
  });
}

/**
 * Registriert zusaetzlich die globalen `window`-Handler (`error`/
 * `unhandledrejection`) — nur ausserhalb von `development` (siehe
 * {@link isReportingEnabled}). `reportClientError`/`reportHandledError`
 * respektieren dasselbe Gate bereits selbst; dieser Aufruf ist nur fuer die
 * globalen Handler noetig, die sonst app-weit bestehen bleiben wuerden.
 */
export function initErrorReporting(): void {
  const environment = process.env.REACT_APP_ENVIRONMENT || 'development';
  if (!isReportingEnabled()) {
    console.log('[errorReporting] Disabled in', environment);
    return;
  }
  defaultReporter.attachGlobalHandlers();
  console.log('[errorReporting] Initialized for', environment);
}
