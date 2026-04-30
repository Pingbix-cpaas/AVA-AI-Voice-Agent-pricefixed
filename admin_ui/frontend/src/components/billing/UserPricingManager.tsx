import React, { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { Save } from 'lucide-react';
import * as billingApi from '../../services/billingApi';
import { useAuth } from '../../auth/AuthContext';

interface PricingPlan {
  id: string;
  name: string;
}

interface UserPricingManagerProps {
  selectedUsername?: string;
  onUserSelect?: (username: string) => void;
}

export const UserPricingManager: React.FC<UserPricingManagerProps> = ({ selectedUsername, onUserSelect }) => {
  const { user } = useAuth();
  const [username, setUsername] = useState(selectedUsername || '');
  const [plans, setPlans] = useState<PricingPlan[]>([]);
  const [loading, setLoading] = useState(false);
  const [useCustom, setUseCustom] = useState(false);
  const [formData, setFormData] = useState({
    plan_id: '',
    credit_limit_inr: 0,
    alert_threshold_pct: 80,
    custom_inr_per_min: undefined as number | undefined,
    custom_inr_per_1k_tokens: undefined as number | undefined,
    custom_inr_per_api_call: undefined as number | undefined,
    custom_inr_per_session: undefined as number | undefined,
    billing_cycle: 'monthly',
  });

  const isAdmin = user?.role === 'super_admin' || user?.role === 'admin';

  useEffect(() => {
    loadPlans();
  }, []);

  useEffect(() => {
    if (selectedUsername) {
      setUsername(selectedUsername);
    }
  }, [selectedUsername]);

  const loadPlans = async () => {
    try {
      const data = await billingApi.getPricingPlans();
      setPlans(data as PricingPlan[]);
    } catch (error) {
      toast.error('Failed to load pricing plans');
      console.error(error);
    }
  };

  const handleAssign = async () => {
    if (!username.trim()) {
      toast.error('Please select a user');
      return;
    }

    try {
      setLoading(true);
      const data = {
        username,
        plan_id: formData.plan_id || undefined,
        credit_limit_inr: formData.credit_limit_inr,
        alert_threshold_pct: formData.alert_threshold_pct,
        billing_cycle: formData.billing_cycle,
      };

      if (useCustom) {
        Object.assign(data, {
          custom_inr_per_min: formData.custom_inr_per_min,
          custom_inr_per_1k_tokens: formData.custom_inr_per_1k_tokens,
          custom_inr_per_api_call: formData.custom_inr_per_api_call,
          custom_inr_per_session: formData.custom_inr_per_session,
        });
      }

      await billingApi.assignUserPricing(data);
      toast.success('User pricing assigned');
      if (onUserSelect) {
        onUserSelect(username);
      }
    } catch (error) {
      toast.error('Failed to assign pricing');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  if (!isAdmin) {
    return <div className="text-red-600">Access denied. Admin only.</div>;
  }

  return (
    <div className="bg-white rounded-lg border p-6 space-y-4">
      <h2 className="text-2xl font-bold">User Pricing Manager</h2>

      <div>
        <label className="block text-sm font-medium mb-2">Select User (username)</label>
        <input
          type="text"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          placeholder="Enter username"
          className="w-full border rounded px-3 py-2"
        />
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">Pricing Plan</label>
        <select
          value={formData.plan_id}
          onChange={(e) => setFormData({ ...formData, plan_id: e.target.value })}
          className="w-full border rounded px-3 py-2"
        >
          <option value="">Select a plan</option>
          {plans.map((plan) => (
            <option key={plan.id} value={plan.id}>
              {plan.name}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">Credit Limit (INR)</label>
        <input
          type="number"
          step="0.01"
          value={formData.credit_limit_inr}
          onChange={(e) => setFormData({ ...formData, credit_limit_inr: parseFloat(e.target.value) })}
          placeholder="0 = unlimited"
          className="w-full border rounded px-3 py-2"
        />
        <small className="text-gray-500">0 = unlimited credit</small>
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">Alert Threshold (%)</label>
        <input
          type="range"
          min="0"
          max="100"
          value={formData.alert_threshold_pct}
          onChange={(e) => setFormData({ ...formData, alert_threshold_pct: parseInt(e.target.value) })}
          className="w-full"
        />
        <div className="text-sm text-gray-600">Alert at {formData.alert_threshold_pct}% of limit</div>
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">Billing Cycle</label>
        <select
          value={formData.billing_cycle}
          onChange={(e) => setFormData({ ...formData, billing_cycle: e.target.value })}
          className="w-full border rounded px-3 py-2"
        >
          <option value="monthly">Monthly</option>
          <option value="pay-as-you-go">Pay-as-you-go</option>
        </select>
      </div>

      <div>
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={useCustom}
            onChange={(e) => setUseCustom(e.target.checked)}
            className="rounded"
          />
          <span className="text-sm font-medium">Use custom rate overrides</span>
        </label>
      </div>

      {useCustom && (
        <div className="bg-gray-50 rounded p-4 space-y-4 border border-gray-200">
          <div>
            <label className="block text-sm font-medium mb-2">Custom INR/min</label>
            <input
              type="number"
              step="0.0001"
              value={formData.custom_inr_per_min ?? ''}
              onChange={(e) => setFormData({ ...formData, custom_inr_per_min: e.target.value ? parseFloat(e.target.value) : undefined })}
              placeholder="Leave empty to use plan rate"
              className="w-full border rounded px-3 py-2"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Custom INR/1K tokens</label>
            <input
              type="number"
              step="0.0001"
              value={formData.custom_inr_per_1k_tokens ?? ''}
              onChange={(e) => setFormData({ ...formData, custom_inr_per_1k_tokens: e.target.value ? parseFloat(e.target.value) : undefined })}
              placeholder="Leave empty to use plan rate"
              className="w-full border rounded px-3 py-2"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Custom INR/API call</label>
            <input
              type="number"
              step="0.0001"
              value={formData.custom_inr_per_api_call ?? ''}
              onChange={(e) => setFormData({ ...formData, custom_inr_per_api_call: e.target.value ? parseFloat(e.target.value) : undefined })}
              placeholder="Leave empty to use plan rate"
              className="w-full border rounded px-3 py-2"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Custom INR/session</label>
            <input
              type="number"
              step="0.0001"
              value={formData.custom_inr_per_session ?? ''}
              onChange={(e) => setFormData({ ...formData, custom_inr_per_session: e.target.value ? parseFloat(e.target.value) : undefined })}
              placeholder="Leave empty to use plan rate"
              className="w-full border rounded px-3 py-2"
            />
          </div>
        </div>
      )}

      <button
        onClick={handleAssign}
        disabled={loading}
        className="w-full flex items-center justify-center gap-2 bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 disabled:bg-gray-400"
      >
        <Save size={18} />
        {loading ? 'Saving...' : 'Save Pricing'}
      </button>
    </div>
  );
};
