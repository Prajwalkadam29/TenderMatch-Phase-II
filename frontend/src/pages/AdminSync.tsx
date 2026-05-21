import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { adminService } from '../services/adminService';
import { useAuth } from '../hooks/useAuth';
import { FiRefreshCw, FiCheckCircle, FiXCircle, FiClock, FiDatabase, FiActivity } from 'react-icons/fi';
import toast from 'react-hot-toast';

export const AdminSync: React.FC = () => {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [isTriggering, setIsTriggering] = useState(false);

  // Quick safety check, normally router handles this
  if (!user || (user.role !== 'SUPER' && user.role !== 'ADMIN1')) {
    return (
      <div className="p-8 text-center text-red-500">
        <h2 className="text-xl font-bold">Access Denied</h2>
        <p>You do not have permission to view this page.</p>
      </div>
    );
  }

  const { data: statusData, isLoading: statusLoading } = useQuery({
    queryKey: ['adminSyncStatus'],
    queryFn: adminService.getSyncStatus,
    refetchInterval: 30000, // Refresh every 30s
  });

  const { data: logsData, isLoading: logsLoading } = useQuery({
    queryKey: ['adminSyncLogs'],
    queryFn: adminService.getSyncLogs,
    refetchInterval: 30000,
  });

  const triggerMutation = useMutation({
    mutationFn: adminService.triggerManualSync,
    onSuccess: () => {
      toast.success('Sync triggered successfully. It will run in the background.');
      queryClient.invalidateQueries({ queryKey: ['adminSyncStatus'] });
      queryClient.invalidateQueries({ queryKey: ['adminSyncLogs'] });
      setIsTriggering(false);
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || 'Failed to trigger sync');
      setIsTriggering(false);
    },
  });

  const handleTriggerSync = () => {
    setIsTriggering(true);
    triggerMutation.mutate();
  };

  const formatDate = (isoString: string | null) => {
    if (!isoString) return 'Never';
    return new Date(isoString).toLocaleString();
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-8">
      <div>
        <h1 className="text-3xl font-extrabold text-gray-900 tracking-tight">Admin Sync Dashboard</h1>
        <p className="mt-1 text-sm text-gray-500">Manage automated tender ingestion from external portals.</p>
      </div>

      {/* Top Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 flex items-center space-x-4">
          <div className="p-3 bg-blue-50 text-blue-600 rounded-lg">
            <FiDatabase size={24} />
          </div>
          <div>
            <p className="text-sm font-medium text-gray-500">Total Tenders</p>
            <p className="text-2xl font-bold text-gray-900">
              {statusLoading ? '...' : statusData?.total_tenders_in_db}
            </p>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 flex items-center space-x-4">
          <div className="p-3 bg-green-50 text-green-600 rounded-lg">
            <FiActivity size={24} />
          </div>
          <div>
            <p className="text-sm font-medium text-gray-500">Bidassist API</p>
            <p className="text-sm font-bold mt-1">
              {statusLoading ? '...' : statusData?.bidassist_connected ? (
                <span className="flex items-center text-green-600"><FiCheckCircle className="mr-1" /> Connected</span>
              ) : (
                <span className="flex items-center text-red-600"><FiXCircle className="mr-1" /> Offline</span>
              )}
            </p>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 flex items-center space-x-4">
          <div className="p-3 bg-purple-50 text-purple-600 rounded-lg">
            <FiClock size={24} />
          </div>
          <div>
            <p className="text-sm font-medium text-gray-500">Last Sync</p>
            <p className="text-sm font-bold text-gray-900 mt-1">
              {statusLoading ? '...' : formatDate(statusData?.last_sync_at || null)}
            </p>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 flex items-center space-x-4">
          <div className="p-3 bg-orange-50 text-orange-600 rounded-lg">
            <FiRefreshCw size={24} />
          </div>
          <div>
            <p className="text-sm font-medium text-gray-500">Next Scheduled Sync</p>
            <p className="text-sm font-bold text-gray-900 mt-1">
              {statusLoading ? '...' : formatDate(statusData?.next_sync_at || null)}
            </p>
          </div>
        </div>
      </div>

      {/* Manual Trigger Section */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-bold text-gray-900">Manual Operations</h3>
            <p className="text-sm text-gray-500 mt-1">Force an immediate sync of external platforms outside the normal schedule.</p>
          </div>
          <button
            onClick={handleTriggerSync}
            disabled={isTriggering}
            className="flex items-center px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition-colors"
          >
            <FiRefreshCw className={`mr-2 ${isTriggering ? 'animate-spin' : ''}`} />
            {isTriggering ? 'Triggering...' : 'Trigger Bidassist Sync'}
          </button>
        </div>
      </div>

      {/* Sync Logs Table */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="px-6 py-5 border-b border-gray-100 bg-gray-50">
          <h3 className="text-lg font-bold text-gray-900">Recent Sync History</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-white">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Time</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Source</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">New</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Dupes</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Errors</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-100">
              {logsLoading ? (
                <tr>
                  <td colSpan={6} className="px-6 py-4 text-center text-sm text-gray-500">Loading logs...</td>
                </tr>
              ) : logsData?.logs?.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-4 text-center text-sm text-gray-500">No sync history available.</td>
                </tr>
              ) : (
                logsData?.logs.map((log, idx) => (
                  <tr key={idx} className="hover:bg-gray-50 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {formatDate(log.started_at)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                        {log.sync_type}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      {log.status === 'success' ? (
                        <span className="flex items-center text-green-600"><FiCheckCircle className="mr-1" /> Success</span>
                      ) : log.status === 'running' ? (
                        <span className="flex items-center text-blue-600"><FiRefreshCw className="mr-1 animate-spin" /> Running</span>
                      ) : (
                        <span className="flex items-center text-red-600"><FiXCircle className="mr-1" /> Failed</span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 font-medium">
                      +{log.new_tenders}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {log.duplicates}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <span className={log.errors > 0 ? "text-red-600 font-medium" : "text-gray-500"}>
                        {log.errors}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default AdminSync;
