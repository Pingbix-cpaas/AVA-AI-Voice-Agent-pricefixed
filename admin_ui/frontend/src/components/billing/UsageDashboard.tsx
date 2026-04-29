import React, { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { Download, ChevronDown } from 'lucide-react';
import * as billingApi from '../../services/billingApi';
import { useAuth } from '../../auth/AuthContext';

interface DashboardDataPoint {
  username: string;
  minutes: number;
  tokens: number;
  api_calls: number;
  sessions: number;
  cost_inr: number;
  limit_inr: number;
  percent_used: number;
  status: 'ok' | 'exceeded';
}

interface UsageEvent {
  id: number;
  username: string;
  event_type: string;
  quantity: number;
  cost_inr: number;
  recorded_at?: string;
}

export const UsageDashboard: React.FC = () => {
  const { user } = useAuth();
  const [dashboardData, setDashboardData] = useState<DashboardDataPoint[]>([]);
  const [usageEvents, setUsageEvents] = useState<Record<string, UsageEvent[]>>({});
  const [loading, setLoading] = useState(true);
  const [expandedUser, setExpandedUser] = useState<string | null>(null);
  const [dateRange, setDateRange] = useState<'this-month' | 'last-month' | 'custom'>('this-month');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  const isAdmin = user?.role === 'super_admin' || user?.role === 'tenant_admin';

  useEffect(() => {
    loadDashboardData();
  }, [dateRange, startDate, endDate]);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      const data = await billingApi.getDashboardData();
      setDashboardData(data);
    } catch (error) {
      toast.error('Failed to load dashboard data');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const loadUsageEvents = async (username: string) => {
    if (usageEvents[username]) {
      return; // Already loaded
    }

    try {
      const start = startDate || undefined;
      const end = endDate || undefined;
      const events = await billingApi.getUsageHistory(username, start, end);
      setUsageEvents((prev) => ({ ...prev, [username]: events }));
    } catch (error) {
      toast.error(`Failed to load usage events for ${username}`);
      console.error(error);
    }
  };

  const getStatusBadge = (status: string, percent: number) => {
    if (status === 'exceeded') {
      return <span className="bg-red-100 text-red-800 px-2 py-1 rounded text-xs font-medium">Exceeded</span>;
    }
    if (percent >= 80) {
      return <span className="bg-yellow-100 text-yellow-800 px-2 py-1 rounded text-xs font-medium">Alert</span>;
    }
    return <span className="bg-green-100 text-green-800 px-2 py-1 rounded text-xs font-medium">OK</span>;
  };

  const exportCSV = () => {
    const csv = [
      ['Username', 'Minutes', 'Tokens', 'API Calls', 'Sessions', 'Cost ₹', 'Limit ₹', '% Used', 'Status'],
      ...dashboardData.map((d) => [
        d.username,
        d.minutes.toFixed(2),
        d.tokens.toString(),
        d.api_calls.toString(),
        d.sessions.toString(),
        d.cost_inr.toFixed(2),
        d.limit_inr.toFixed(2),
        d.percent_used.toFixed(1),
        d.status,
      ]),
    ]
      .map((row) => row.join(','))
      .join('\n');

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `billing_usage_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  if (!isAdmin) {
    return <div className="text-red-600">Access denied. Admin only.</div>;
  }

  if (loading) {
    return <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>;
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold">Usage Dashboard</h2>
        <div className="flex gap-2">
          <select
            value={dateRange}
            onChange={(e) => setDateRange(e.target.value as any)}
            className="border rounded px-3 py-2 text-sm"
          >
            <option value="this-month">This Month</option>
            <option value="last-month">Last Month</option>
            <option value="custom">Custom Range</option>
          </select>
          <button
            onClick={exportCSV}
            className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 text-sm"
          >
            <Download size={16} />
            Export CSV
          </button>
        </div>
      </div>

      {dateRange === 'custom' && (
        <div className="flex gap-4 bg-gray-50 p-4 rounded border">
          <div>
            <label className="block text-sm font-medium mb-1">Start Date</label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="border rounded px-3 py-2"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">End Date</label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="border rounded px-3 py-2"
            />
          </div>
        </div>
      )}

      <div className="overflow-x-auto border rounded">
        <table className="w-full text-sm">
          <thead className="bg-gray-100 border-b">
            <tr>
              <th className="p-3 text-left">User</th>
              <th className="p-3 text-right">Minutes</th>
              <th className="p-3 text-right">Tokens</th>
              <th className="p-3 text-right">API Calls</th>
              <th className="p-3 text-right">Sessions</th>
              <th className="p-3 text-right">Cost ₹</th>
              <th className="p-3 text-right">Limit ₹</th>
              <th className="p-3 text-right">% Used</th>
              <th className="p-3 text-center">Status</th>
              <th className="p-3 text-center">Details</th>
            </tr>
          </thead>
          <tbody>
            {dashboardData.map((row) => (
              <React.Fragment key={row.username}>
                <tr className="border-b hover:bg-gray-50">
                  <td className="p-3 font-medium">{row.username}</td>
                  <td className="p-3 text-right">{row.minutes.toFixed(2)}</td>
                  <td className="p-3 text-right">{row.tokens}</td>
                  <td className="p-3 text-right">{row.api_calls}</td>
                  <td className="p-3 text-right">{row.sessions}</td>
                  <td className="p-3 text-right">₹{row.cost_inr.toFixed(2)}</td>
                  <td className="p-3 text-right">₹{row.limit_inr.toFixed(2)}</td>
                  <td className="p-3 text-right">
                    <div className="w-full bg-gray-200 rounded h-2">
                      <div
                        className={`h-full rounded ${
                          row.status === 'exceeded' ? 'bg-red-500' : row.percent_used >= 80 ? 'bg-yellow-500' : 'bg-green-500'
                        }`}
                        style={{ width: `${Math.min(row.percent_used, 100)}%` }}
                      ></div>
                    </div>
                    <small>{row.percent_used.toFixed(1)}%</small>
                  </td>
                  <td className="p-3 text-center">{getStatusBadge(row.status, row.percent_used)}</td>
                  <td className="p-3 text-center">
                    <button
                      onClick={() => {
                        setExpandedUser(expandedUser === row.username ? null : row.username);
                        if (expandedUser !== row.username) {
                          loadUsageEvents(row.username);
                        }
                      }}
                      className="text-blue-600 hover:text-blue-800"
                    >
                      <ChevronDown size={18} className={expandedUser === row.username ? 'rotate-180' : ''} />
                    </button>
                  </td>
                </tr>
                {expandedUser === row.username && usageEvents[row.username] && (
                  <tr className="bg-gray-50 border-b">
                    <td colSpan={10} className="p-4">
                      <div className="space-y-2">
                        <h4 className="font-medium">Recent Usage Events</h4>
                        <div className="bg-white border rounded max-h-64 overflow-y-auto">
                          <table className="w-full text-xs">
                            <thead className="bg-gray-100 sticky top-0">
                              <tr>
                                <th className="p-2 text-left">Type</th>
                                <th className="p-2 text-right">Qty</th>
                                <th className="p-2 text-right">Cost ₹</th>
                                <th className="p-2 text-left">Date</th>
                              </tr>
                            </thead>
                            <tbody>
                              {usageEvents[row.username].slice(0, 20).map((event) => (
                                <tr key={event.id} className="border-t">
                                  <td className="p-2">{event.event_type}</td>
                                  <td className="p-2 text-right">{event.quantity.toFixed(2)}</td>
                                  <td className="p-2 text-right">₹{event.cost_inr.toFixed(4)}</td>
                                  <td className="p-2">{event.recorded_at?.split('T')[0]}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
