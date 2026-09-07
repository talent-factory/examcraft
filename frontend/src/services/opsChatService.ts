import { postJson } from './httpClient';
import { OpsChatTurn } from '../types/opsChat';

interface OpsChatResponse {
  reply: string;
}

/**
 * Sends one Ops-Chat turn (TF-787). `history` is the full prior
 * conversation — the backend persists nothing, so it must be resent on
 * every call. Superuser-only on the backend (403 for anyone else).
 */
export async function sendOpsChatMessage(
  message: string,
  history: OpsChatTurn[],
): Promise<string> {
  const response = await postJson<OpsChatResponse>('/api/v1/ops/chat', { message, history });
  return response.reply;
}
