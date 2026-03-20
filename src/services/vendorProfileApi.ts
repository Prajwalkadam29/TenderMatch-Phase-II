import api from './api';
import type { VendorProfilePayload, VendorProfileResponse } from '../types/vendorProfile';

export const vendorProfileService = {
  create: (payload: VendorProfilePayload): Promise<VendorProfileResponse> =>
    api.post('/vendor-profiles/', payload).then(r => r.data),

  list: (): Promise<VendorProfileResponse[]> =>
    api.get('/vendor-profiles/').then(r => r.data),

  get: (id: string): Promise<VendorProfileResponse> =>
    api.get(`/vendor-profiles/${id}`).then(r => r.data),

  update: (id: string, payload: VendorProfilePayload): Promise<VendorProfileResponse> =>
    api.put(`/vendor-profiles/${id}`, payload).then(r => r.data),

  delete: (id: string): Promise<void> =>
    api.delete(`/vendor-profiles/${id}`).then(r => r.data),
};
