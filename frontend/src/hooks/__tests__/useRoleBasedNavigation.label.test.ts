import * as fs from 'fs';
import * as path from 'path';

describe('useRoleBasedNavigation - Tag Label', () => {
  it('uses tag-settings translation key (not myTags fallback)', () => {
    const hookFile = path.resolve(__dirname, '../useRoleBasedNavigation.ts');
    const content = fs.readFileSync(hookFile, 'utf8');

    // Der Hook sollte den i18n-Key 'nav.sidebar.tagSettings' verwenden
    expect(content).toContain("t('nav.sidebar.tagSettings'");

    // Der Hook sollte NICHT mehr den alten Key 'nav.sidebar.myTags' verwenden
    expect(content).not.toContain("t('nav.sidebar.myTags'");
  });

  it('tag navigation item has correct path and icon', () => {
    const hookFile = path.resolve(__dirname, '../useRoleBasedNavigation.ts');
    const content = fs.readFileSync(hookFile, 'utf8');

    // Überprüfe dass der Pfad korrekt ist
    expect(content).toContain("path: '/settings/tags'");

    // Überprüfe dass das Icon 🏷 vorhanden ist
    expect(content).toContain("icon: '🏷'");
  });

  it('tag navigation item restricts to DOZENT and ASSISTANT roles', () => {
    const hookFile = path.resolve(__dirname, '../useRoleBasedNavigation.ts');
    const content = fs.readFileSync(hookFile, 'utf8');

    // Überprüfe dass die Rolle-Anforderungen korrekt sind
    expect(content).toContain('requiredRoles: [UserRole.DOZENT, UserRole.ASSISTANT]');
    expect(content).toContain('excludedRoles: [UserRole.ADMIN]');
    expect(content).toContain('excludeSuperuser: true');
  });
});
