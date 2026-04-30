import React, { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { RotateCcw, AlertTriangle } from 'lucide-react';
import * as billingApi from '../../services/billingApi';
import { useAuth } from '../../auth/AuthContext';

interface BillingSummary {
  username: string;
  billing_month: string;
  total_minutes: number;
  total_tokens: number;
  total_api_calls: number;
  total_sessions: number;
  total_cost_inr: number;
  flat_fee_inr: number;
  grand_total_inr: number;
}

export const BillingSummary: React.FC = () => {
  const { user } = useAuth();
  const [summaries, setSummaries] = useState<Record<string, BillingSummary>>({});
  const [loading, setLoading] = useState(false);
  const [selectedMonth, setSelectedMonth] = useState(() => {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
  });
  const [username, setUsername] = useState('');

  const isAdmin = user?.role === 'super_admin' || user?.role === 'admin';
  const isSuperAdmin = user?.role === 'super_admin';

  useEffect(() => {
    if (user && !isAdmin) {
      setUsername(user.username || '');
    }
  }, [user, isAdmin]);

  const loadSummary = async () => {
    const targetUsername = username || user?.username;
    if (!targetUsername) {
      toast.error('Please provide a username');
      return;
    }

    try {
      setLoading(true);
      const summary = await billingApi.getMonthlySummary(targetUsername, selectedMonth);
      setSummaries((prev) => ({ ...prev, [targetUsername]: summary }));
    } catch (error: any) {
      if (error.response?.status === 404) {
        toast.info('No summary found for this month');
        setSummaries((prev) => ({ ...prev, [targetUsername]: undefined as any }));
      } else {
        toast.error('Failed to load billing summary');
        console.error(error);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async (summary: BillingSummary) => {
    if (!isSuperAdmin) {
      toast.error('Only super admins can reset usage');
      return;
    }

    if (!window.confirm(`Reset usage for ${summary.username} in ${summary.billing_month}?`)) {
      return;
    }

    try {
      await billingApi.resetUserUsage(summary.username, summary.billing_month);
      toast.success('Usage reset');
      loadSummary();
    } catch (error) {
      toast.error('Failed to reset usage');
      console.error(error);
    }
  };

  const currentSummary = summaries[username || user?.username || ''];

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold">Billing Summary</h2>

      <div className="bg-white rounded-lg border p-4 space-y-4">
        <div className="grid grid-cols-3 gap-4">
          {isAdmin && (
            <div>
              <label className="block text-sm font-medium mb-2">User (username)</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Leave empty for self"
                className="w-full border rounded px-3 py-2"
              />
            </div>
          )}

          <div className={isAdmin ? '' : 'col-span-2'}>
            <label className="block text-sm font-medium mb-2">Billing Month</label>
            <input
              type="month"
              value={selectedMonth}
              onChange={(e) => setSelectedMonth(e.target.value)}
              className="w-full border rounded px-3 py-2"
            />
          </div>

          <div className="flex items-end">
            <button
              onClick={loadSummary}
              disabled={loading}
              className="w-full bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:bg-gray-400"
            >
              {loading ? 'Loading...' : 'Load'}
            </button>
          </div>
        </div>
      </div>

      {currentSummary ? (
        <div className="bg-white rounded-lg border p-6 space-y-4">
          <div className="flex justify-between items-start">
            <div>
              <h3 className="text-lg font-bold">{currentSummary.username}</h3>
              <p className="text-gray-600">{currentSummary.billing_month}</p>
            </div>
            {isSuperAdmin && (
              <button
                onClick={() => handleReset(currentSummary)}
                className="flex items-center gap-2 bg-red-600 text-white px-3 py-2 rounded hover:bg-red-700 text-sm"
              >
                <RotateCcw size={16} />
                Reset Usage
              </button>
            )}
          </div>

          {currentSummary.grand_total_inr > 0 && (
            <div className="bg-blue-50 border border-blue-200 rounded p-3 flex items-start gap-3">
              <AlertTriangle size={18} className="text-blue-600 mt-0.5" />
              <div className="text-sm">
                <strong>Progress:</strong> ₹{currentSummary.grand_total_inr.toFixed(2)} / ∞
              </div>
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div className="bg-gray-50 rounded p-4 border">
              <p className="text-sm text-gray-600 mb-1">Call Minutes</p>
              <p className="text-2xl font-bold">{currentSummary.total_minutes.toFixed(2)}</p>
              <p className="text-xs text-gray-500 mt-2">₹{(currentSummary.total_minutes * (currentSummary.total_cost_inr / (currentSummary.total_minutes || 1))).toFixed(2)}</p>
            </div>

            <div className="bg-gray-50 rounded p-4 border">
              <p className="text-sm text-gray-600 mb-1">Tokens</p>
              <p className="text-2xl font-bold">{currentSummary.total_tokens}</p>
              <p className="text-xs text-gray-500 mt-2">₹{(currentSummary.total_tokens * (currentSummary.total_cost_inr / (currentSummary.total_minutes || 1))).toFixed(2)}</p>
            </div>

            <div className="bg-gray-50 rounded p-4 border">
              <p className="text-sm text-gray-600 mb-1">API Calls</p>
              <p className="text-2xl font-bold">{currentSummary.total_api_calls}</p>
              <p className="text-xs text-gray-500 mt-2">₹{(currentSummary.total_api_calls * (currentSummary.total_cost_inr / (currentSummary.total_minutes || 1))).toFixed(2)}</p>
            </div>

            <div className="bg-gray-50 rounded p-4 border">
              <p className="text-sm text-gray-600 mb-1">Sessions</p>
              <p className="text-2xl font-bold">{currentSummary.total_sessions}</p>
              <p className="text-xs text-gray-500 mt-2">₹{(currentSummary.total_sessions * (currentSummary.total_cost_inr / (currentSummary.total_minutes || 1))).toFixed(2)}</p>
            </div>
          </div>

          <div className="border-t pt-4 space-y-2">
            <div className="flex justify-between text-sm">
              <span>Usage Charges:</span>
              <span>₹{currentSummary.total_cost_inr.toFixed(4)}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span>Flat Fee:</span>
              <span>₹{currentSummary.flat_fee_inr.toFixed(2)}</span>
            </div>
            <div className="flex justify-between font-bold text-lg border-t pt-2">
              <span>Grand Total:</span>
              <span className="text-green-600">₹{currentSummary.grand_total_inr.toFixed(2)}</span>
            </div>
          </div>
        </div>
      ) : (
        <div className="text-center text-gray-500 py-8">
          No summary available. Load a billing month above.
        </div>
      )}
    </div>
  );
};
