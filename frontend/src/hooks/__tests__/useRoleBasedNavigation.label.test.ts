import * as fs from 'fs';
import * as path from 'path';

describe('useRoleBasedNavigation - Tag Label', () => {
  it('uses tag-settings translation key (not myTags fallback)', () => {
    const hookFile = path.resolve(__dirname, '../useRoleBasedNavigation.ts');
    const content = fs.readFileSync(hookFile, 'utf8');

    // The hook should use the i18n key 'nav.sidebar.tagSettings'
    expect(content).toContain("t('nav.sidebar.tagSettings'");

    // The hook should NOT use the old key 'nav.sidebar.myTags' anymore
    expect(content).not.toContain("t('nav.sidebar.myTags'");
  });

  it('tag navigation item has correct path and icon', () => {
    const hookFile = path.resolve(__dirname, '../useRoleBasedNavigation.ts');
    const content = fs.readFileSync(hookFile, 'utf8');

    // Check that the path is correct
    expect(content).toContain("path: '/settings/tags'");

    // Check that the 🏷 icon is present
    expect(content).toContain("icon: '🏷'");
  });

  it('tag navigation item restricts to DOZENT and ASSISTANT roles', () => {
    const hookFile = path.resolve(__dirname, '../useRoleBasedNavigation.ts');
    const content = fs.readFileSync(hookFile, 'utf8');

    // Check that the role requirements are correct
    expect(content).toContain('requiredRoles: [UserRole.DOZENT, UserRole.ASSISTANT]');
    expect(content).toContain('excludedRoles: [UserRole.ADMIN]');
    expect(content).toContain('excludeSuperuser: true');
  });
});
