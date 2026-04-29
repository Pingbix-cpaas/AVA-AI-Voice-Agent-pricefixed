import React, { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { Trash2, Edit2, Plus } from 'lucide-react';
import * as billingApi from '../../services/billingApi';
import { useAuth } from '../../auth/AuthContext';

interface PricingPlan {
  id: string;
  name: string;
  inr_per_min: number;
  inr_per_1k_tokens: number;
  inr_per_api_call: number;
  inr_per_session: number;
  flat_monthly_inr: number;
}

export const PricingPlansList: React.FC = () => {
  const { user } = useAuth();
  const [plans, setPlans] = useState<PricingPlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingPlan, setEditingPlan] = useState<PricingPlan | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    inr_per_min: 0,
    inr_per_1k_tokens: 0,
    inr_per_api_call: 0,
    inr_per_session: 0,
    flat_monthly_inr: 0,
  });

  const isSuperAdmin = user?.role === 'super_admin';

  useEffect(() => {
    loadPlans();
  }, []);

  const loadPlans = async () => {
    try {
      setLoading(true);
      const data = await billingApi.getPricingPlans();
      setPlans(data);
    } catch (error) {
      toast.error('Failed to load pricing plans');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    try {
      await billingApi.createPricingPlan(formData);
      toast.success('Pricing plan created');
      setShowModal(false);
      setFormData({
        name: '',
        inr_per_min: 0,
        inr_per_1k_tokens: 0,
        inr_per_api_call: 0,
        inr_per_session: 0,
        flat_monthly_inr: 0,
      });
      loadPlans();
    } catch (error) {
      toast.error('Failed to create pricing plan');
      console.error(error);
    }
  };

  const handleUpdate = async () => {
    if (!editingPlan) return;
    try {
      await billingApi.updatePricingPlan(editingPlan.id, formData);
      toast.success('Pricing plan updated');
      setShowModal(false);
      setEditingPlan(null);
      loadPlans();
    } catch (error) {
      toast.error('Failed to update pricing plan');
      console.error(error);
    }
  };

  const handleDelete = async (planId: string) => {
    if (!window.confirm('Are you sure you want to delete this plan?')) return;
    try {
      await billingApi.deletePricingPlan(planId);
      toast.success('Pricing plan deleted');
      loadPlans();
    } catch (error) {
      toast.error('Failed to delete pricing plan');
      console.error(error);
    }
  };

  const openEditModal = (plan: PricingPlan) => {
    setEditingPlan(plan);
    setFormData(plan);
    setShowModal(true);
  };

  if (!isSuperAdmin) {
    return <div className="text-red-600">Access denied. Super admin only.</div>;
  }

  if (loading) {
    return <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>;
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold">Pricing Plans</h2>
        <button
          onClick={() => {
            setEditingPlan(null);
            setFormData({
              name: '',
              inr_per_min: 0,
              inr_per_1k_tokens: 0,
              inr_per_api_call: 0,
              inr_per_session: 0,
              flat_monthly_inr: 0,
            });
            setShowModal(true);
          }}
          className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          <Plus size={18} />
          Create Plan
        </button>
      </div>

      <div className="overflow-x-auto border rounded">
        <table className="w-full text-sm">
          <thead className="bg-gray-100 border-b">
            <tr>
              <th className="p-3 text-left">Name</th>
              <th className="p-3 text-left">INR/min</th>
              <th className="p-3 text-left">INR/1K tokens</th>
              <th className="p-3 text-left">INR/call</th>
              <th className="p-3 text-left">INR/session</th>
              <th className="p-3 text-left">Flat fee</th>
              <th className="p-3 text-center">Actions</th>
            </tr>
          </thead>
          <tbody>
            {plans.map((plan) => (
              <tr key={plan.id} className="border-b hover:bg-gray-50">
                <td className="p-3">{plan.name}</td>
                <td className="p-3">₹{plan.inr_per_min.toFixed(4)}</td>
                <td className="p-3">₹{plan.inr_per_1k_tokens.toFixed(4)}</td>
                <td className="p-3">₹{plan.inr_per_api_call.toFixed(4)}</td>
                <td className="p-3">₹{plan.inr_per_session.toFixed(4)}</td>
                <td className="p-3">₹{plan.flat_monthly_inr.toFixed(2)}</td>
                <td className="p-3 text-center flex gap-2 justify-center">
                  <button
                    onClick={() => openEditModal(plan)}
                    className="text-blue-600 hover:text-blue-800"
                  >
                    <Edit2 size={18} />
                  </button>
                  <button
                    onClick={() => handleDelete(plan.id)}
                    className="text-red-600 hover:text-red-800"
                  >
                    <Trash2 size={18} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-8 w-96 shadow-xl">
            <h3 className="text-xl font-bold mb-4">
              {editingPlan ? 'Edit Plan' : 'Create Plan'}
            </h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Name</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full border rounded px-3 py-2"
                  disabled={!!editingPlan}
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">INR per minute</label>
                <input
                  type="number"
                  step="0.0001"
                  value={formData.inr_per_min}
                  onChange={(e) => setFormData({ ...formData, inr_per_min: parseFloat(e.target.value) })}
                  className="w-full border rounded px-3 py-2"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">INR per 1K tokens</label>
                <input
                  type="number"
                  step="0.0001"
                  value={formData.inr_per_1k_tokens}
                  onChange={(e) => setFormData({ ...formData, inr_per_1k_tokens: parseFloat(e.target.value) })}
                  className="w-full border rounded px-3 py-2"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">INR per API call</label>
                <input
                  type="number"
                  step="0.0001"
                  value={formData.inr_per_api_call}
                  onChange={(e) => setFormData({ ...formData, inr_per_api_call: parseFloat(e.target.value) })}
                  className="w-full border rounded px-3 py-2"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">INR per session</label>
                <input
                  type="number"
                  step="0.0001"
                  value={formData.inr_per_session}
                  onChange={(e) => setFormData({ ...formData, inr_per_session: parseFloat(e.target.value) })}
                  className="w-full border rounded px-3 py-2"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Flat monthly fee (INR)</label>
                <input
                  type="number"
                  step="0.01"
                  value={formData.flat_monthly_inr}
                  onChange={(e) => setFormData({ ...formData, flat_monthly_inr: parseFloat(e.target.value) })}
                  className="w-full border rounded px-3 py-2"
                />
              </div>
            </div>
            <div className="flex gap-2 mt-6">
              <button
                onClick={() => {
                  setShowModal(false);
                  setEditingPlan(null);
                }}
                className="flex-1 bg-gray-200 px-4 py-2 rounded hover:bg-gray-300"
              >
                Cancel
              </button>
              <button
                onClick={editingPlan ? handleUpdate : handleCreate}
                className="flex-1 bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
              >
                {editingPlan ? 'Update' : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
