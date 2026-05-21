import { isPendingTag, type PendingTag, type Tag, type TagValue } from '../tagsApi';

describe('isPendingTag', () => {
  it('erkennt PendingTag', () => {
    const p: PendingTag = { __pending: true, name: 'Thermodynamik' };
    expect(isPendingTag(p)).toBe(true);
  });

  it('erkennt echten Tag als nicht-pending', () => {
    const t: Tag = {
      id: 42,
      name: 'Thermodynamik',
      scope: 'institution',
      institution_id: 1,
      usage_count: 3,
      is_archived: false,
      is_own: true,
    };
    expect(isPendingTag(t)).toBe(false);
  });

  it('gibt false zurück wenn __pending=false (runtime-Schutz)', () => {
    const fakeTag = { __pending: false, name: 'X' } as unknown as TagValue;
    expect(isPendingTag(fakeTag)).toBe(false);
  });
});
