// types/pagination.types.ts

import type {
  AuswertungBahnIDs,
  AuswertungInfo,
} from '@/types/auswertung.types';
import type { BahnInfo, BahnInfoRaw } from '@/types/bewegungsdaten.types';

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

export interface BahnInfoResponseRaw {
  bahn_info: BahnInfoRaw[];
  pagination: PaginationResultRaw;
}

export interface BahnInfoResponse {
  bahnInfo: BahnInfo[];
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

export interface AuswertungInfoResponse {
  auswertungInfo: AuswertungInfo;
  pagination: {
    total: number;
    page: number;
    pageSize: number;
    totalPages: number;
    hasNext: boolean;
    hasPrevious: boolean;
  };
}

export interface AuswertungIDsResponse {
  auswertungBahnIDs: AuswertungBahnIDs;
  pagination: {
    total: number;
    page: number;
    pageSize: number;
    totalPages: number;
    hasNext: boolean;
    hasPrevious: boolean;
  };
}
