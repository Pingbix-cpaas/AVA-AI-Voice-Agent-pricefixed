import React, { useState } from 'react';
import { useAuth } from '../../auth/AuthContext';
import { PricingPlansList } from './PricingPlansList';
import { UserPricingManager } from './UserPricingManager';
import { UsageDashboard } from './UsageDashboard';
import { BillingSummary } from './BillingSummary';

export const BillingDashboard: React.FC = () => {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<'overview' | 'plans' | 'assign' | 'usage' | 'summary'>('overview');

  const isAdmin = user?.role === 'super_admin' || user?.role === 'admin';
  const isSuperAdmin = user?.role === 'super_admin';

  if (!isAdmin) {
    return (
      <div className="p-8 text-center">
        <h1 className="text-2xl font-bold text-red-600 mb-2">Access Denied</h1>
        <p className="text-gray-600">You don't have permission to access the billing dashboard.</p>
      </div>
    );
  }

  const tabs = [
    { id: 'overview', label: 'Overview', show: true },
    { id: 'plans', label: 'Pricing Plans', show: isSuperAdmin },
    { id: 'assign', label: 'User Assignment', show: true },
    { id: 'usage', label: 'Usage Monitor', show: true },
    { id: 'summary', label: 'Monthly Summary', show: true },
  ].filter((tab) => tab.show);

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <h1 className="text-3xl font-bold">Billing Dashboard</h1>
          <p className="text-gray-600 mt-1">Manage pricing plans, track usage, and monitor costs</p>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-6">
        {/* Tabs */}
        <div className="flex gap-2 mb-6 border-b bg-white rounded-t">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`px-4 py-3 font-medium border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-600 hover:text-gray-900'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="bg-white rounded-b p-6">
          {activeTab === 'overview' && (
            <div className="space-y-6">
              <div className="grid grid-cols-3 gap-4">
                <div className="bg-blue-50 rounded p-6 border border-blue-200">
                  <p className="text-sm text-gray-600 mb-2">Total Active Users</p>
                  <p className="text-3xl font-bold text-blue-600">0</p>
                </div>
                <div className="bg-green-50 rounded p-6 border border-green-200">
                  <p className="text-sm text-gray-600 mb-2">Pricing Plans</p>
                  <p className="text-3xl font-bold text-green-600">0</p>
                </div>
                <div className="bg-purple-50 rounded p-6 border border-purple-200">
                  <p className="text-sm text-gray-600 mb-2">This Month Revenue</p>
                  <p className="text-3xl font-bold text-purple-600">₹0.00</p>
                </div>
              </div>

              <div className="bg-blue-50 border border-blue-200 rounded p-4">
                <h3 className="font-bold text-blue-900 mb-2">📊 Billing System Status</h3>
                <ul className="text-sm text-blue-800 space-y-1">
                  <li>✓ Pricing plans system enabled</li>
                  <li>✓ Usage tracking active</li>
                  <li>✓ Monthly billing cycles configured</li>
                  <li>✓ Real-time cost calculation</li>
                </ul>
              </div>

              <div className="border-t pt-6">
                <h3 className="text-lg font-bold mb-4">Quick Start</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-gray-50 rounded p-4 border hover:shadow-md transition-shadow cursor-pointer" onClick={() => setActiveTab('plans')}>
                    <p className="font-medium mb-2">1. Create Pricing Plans</p>
                    <p className="text-sm text-gray-600">Define your rate structure for minutes, tokens, API calls, and sessions.</p>
                  </div>
                  <div className="bg-gray-50 rounded p-4 border hover:shadow-md transition-shadow cursor-pointer" onClick={() => setActiveTab('assign')}>
                    <p className="font-medium mb-2">2. Assign Plans to Users</p>
                    <p className="text-sm text-gray-600">Link pricing plans to users and set credit limits and alerts.</p>
                  </div>
                  <div className="bg-gray-50 rounded p-4 border hover:shadow-md transition-shadow cursor-pointer" onClick={() => setActiveTab('usage')}>
                    <p className="font-medium mb-2">3. Monitor Usage</p>
                    <p className="text-sm text-gray-600">Track real-time usage and costs across all users.</p>
                  </div>
                  <div className="bg-gray-50 rounded p-4 border hover:shadow-md transition-shadow cursor-pointer" onClick={() => setActiveTab('summary')}>
                    <p className="font-medium mb-2">4. Review Billing</p>
                    <p className="text-sm text-gray-600">View monthly summaries and billing breakdowns.</p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'plans' && isSuperAdmin && <PricingPlansList />}

          {activeTab === 'assign' && <UserPricingManager />}

          {activeTab === 'usage' && <UsageDashboard />}

          {activeTab === 'summary' && <BillingSummary />}
        </div>
      </div>
    </div>
  );
};

export default BillingDashboard;
