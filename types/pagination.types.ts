// types/pagination.types.ts

import type {
  EvaluationTrajIDs,
  EvaluationInfo,
} from '@/types/evaluation.types';
import type { TrajInfo, TrajInfoRaw } from '@/types/motion.types';

export interface PaginationParams {
  page?: number;
  pageSize?: number;
}

export interface PaginationResultRaw {
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
}

export interface TrajInfoResponseRaw {
  traj_info: TrajInfoRaw[];
  pagination: PaginationResultRaw;
}

export interface TrajInfoResponse {
  trajInfo: TrajInfo[];
  pagination: PaginationResult;
}

export interface PaginationResult {
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
  hasNext: boolean;
  hasPrevious: boolean;
}

export interface EvaluationInfoResponse {
  evaluationInfo: EvaluationInfo;
  pagination: {
    total: number;
    page: number;
    pageSize: number;
    totalPages: number;
    hasNext: boolean;
    hasPrevious: boolean;
  };
}

export interface EvaluationIDsResponse {
  evaluationTrajIDs: EvaluationTrajIDs;
  pagination: {
    total: number;
    page: number;
    pageSize: number;
    totalPages: number;
    hasNext: boolean;
    hasPrevious: boolean;
  };
}
