import api from './api';

export interface SyncLog {
  sync_type: string;
  started_at: string;
  completed_at: string | null;
  status: string;
  new_tenders: number;
  duplicates: number;
  errors: number;
  portals_scraped: number;
}

export interface SyncStatus {
  last_sync_at: string | null;
  next_sync_at: string | null;
  total_tenders_in_db: number;
  bidassist_connected: boolean;
}

export const adminService = {
  triggerManualSync: async () => {
    const response = await api.post('/admin/sync/trigger');
    return response.data;
  },

  getSyncLogs: async (): Promise<{ logs: SyncLog[] }> => {
    const response = await api.get('/admin/sync/logs');
    return response.data;
  },

  getSyncStatus: async (): Promise<SyncStatus> => {
    const response = await api.get('/admin/sync/status');
    return response.data;
  }
};
