/**
 * ComplianceService — wraps the public compliance-document API (TF-746).
 *
 * GET /api/v1/legal/compliance is unauthenticated (prospective school
 * customers need to read the AVV/TOM before they have an account), so
 * this uses plain ``fetch`` rather than the auth-retry-aware
 * ``httpClient`` helpers — there is no token to refresh.
 *
 * The failure path throws an AppError (TF-671): CompliancePage only renders a
 * translated generic message, but the code keeps that a property of the error
 * rather than an accident of the caller.
 */
import { AppError } from '../errors';

export const API_BASE_URL =
  process.env.REACT_APP_API_URL || 'http://localhost:8000';

export const AVV_PDF_URL = `${API_BASE_URL}/api/v1/legal/avv.pdf`;
export const TOM_PDF_URL = `${API_BASE_URL}/api/v1/legal/tom.pdf`;

export interface ComplianceSection {
  heading: string;
  paragraphs: string[];
}

export interface ComplianceDocument {
  title: string;
  last_updated: string;
  draft_notice: string;
  sections: ComplianceSection[];
}

export interface Subprocessor {
  name: string;
  purpose: string;
  location: string;
  transfer_mechanism: string;
  change_notice: string;
}

export interface ComplianceContent {
  avv: ComplianceDocument;
  tom: ComplianceDocument;
  subprocessors: Subprocessor[];
  vvt_text: string;
  state_specific_notes: ComplianceSection;
}

export class ComplianceService {
  static async getContent(): Promise<ComplianceContent> {
    const response = await fetch(`${API_BASE_URL}/api/v1/legal/compliance`);
    if (!response.ok) {
      throw new AppError(
        'compliance.loadFailed',
        `Failed to load compliance content (${response.status})`,
        response.status,
      );
    }
    return (await response.json()) as ComplianceContent;
  }
}
