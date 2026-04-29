import axios from 'axios';

const API_BASE = '/api/billing';

export interface PricingPlan {
  id: string;
  name: string;
  created_by: string;
  inr_per_min: number;
  inr_per_1k_tokens: number;
  inr_per_api_call: number;
  inr_per_session: number;
  flat_monthly_inr: number;
  created_at?: string;
  updated_at?: string;
}

export interface UserPricing {
  id: string;
  username: string;
  plan_id?: string;
  credit_limit_inr: number;
  alert_threshold_pct: number;
  custom_inr_per_min?: number;
  custom_inr_per_1k_tokens?: number;
  custom_inr_per_api_call?: number;
  custom_inr_per_session?: number;
  billing_cycle: string;
  assigned_by?: string;
  assigned_at?: string;
}

export interface UsageEvent {
  id: number;
  username: string;
  event_type: string;
  quantity: number;
  cost_inr: number;
  event_metadata?: Record<string, any>;
  recorded_at?: string;
}

export interface BillingSummary {
  id: number;
  username: string;
  billing_month: string;
  total_minutes: number;
  total_tokens: number;
  total_api_calls: number;
  total_sessions: number;
  total_cost_inr: number;
  flat_fee_inr: number;
  grand_total_inr: number;
  created_at?: string;
  updated_at?: string;
}

export interface DashboardDataPoint {
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

// ============================================================================
// Pricing Plans
// ============================================================================

export const getPricingPlans = async (): Promise<PricingPlan[]> => {
  const res = await axios.get(`${API_BASE}/plans`);
  return res.data.plans;
};

export const createPricingPlan = async (data: {
  name: string;
  inr_per_min: number;
  inr_per_1k_tokens: number;
  inr_per_api_call: number;
  inr_per_session: number;
  flat_monthly_inr: number;
}): Promise<PricingPlan> => {
  const res = await axios.post(`${API_BASE}/plans`, data);
  return res.data.plan;
};

export const updatePricingPlan = async (
  planId: string,
  data: Partial<{
    inr_per_min: number;
    inr_per_1k_tokens: number;
    inr_per_api_call: number;
    inr_per_session: number;
    flat_monthly_inr: number;
  }>
): Promise<PricingPlan> => {
  const res = await axios.put(`${API_BASE}/plans/${planId}`, data);
  return res.data.plan;
};

export const deletePricingPlan = async (planId: string): Promise<void> => {
  await axios.delete(`${API_BASE}/plans/${planId}`);
};

// ============================================================================
// User Pricing
// ============================================================================

export const assignUserPricing = async (data: {
  username: string;
  plan_id?: string;
  credit_limit_inr: number;
  alert_threshold_pct: number;
  custom_inr_per_min?: number;
  custom_inr_per_1k_tokens?: number;
  custom_inr_per_api_call?: number;
  custom_inr_per_session?: number;
  billing_cycle: string;
}): Promise<UserPricing> => {
  const res = await axios.post(`${API_BASE}/assign`, data);
  return res.data.user_pricing;
};

export const getUserPricing = async (username: string): Promise<UserPricing> => {
  const res = await axios.get(`${API_BASE}/user/${username}`);
  return res.data.user_pricing;
};

export const updateUserPricing = async (
  username: string,
  data: Partial<{
    credit_limit_inr: number;
    alert_threshold_pct: number;
    custom_inr_per_min: number;
    custom_inr_per_1k_tokens: number;
    custom_inr_per_api_call: number;
    custom_inr_per_session: number;
    billing_cycle: string;
  }>
): Promise<UserPricing> => {
  const res = await axios.put(`${API_BASE}/user/${username}`, data);
  return res.data.user_pricing;
};

// ============================================================================
// Usage Recording
// ============================================================================

export const recordUsageEvent = async (data: {
  username: string;
  event_type: 'minutes' | 'tokens' | 'api_call' | 'session';
  quantity: number;
  event_metadata?: Record<string, any>;
}): Promise<UsageEvent> => {
  const res = await axios.post(`${API_BASE}/usage/record`, data);
  return res.data.event;
};

export const getUsageHistory = async (
  username: string,
  startDate?: string,
  endDate?: string
): Promise<UsageEvent[]> => {
  const params: Record<string, string> = {};
  if (startDate) params.start_date = startDate;
  if (endDate) params.end_date = endDate;

  const res = await axios.get(`${API_BASE}/usage/${username}`, { params });
  return res.data.events;
};

// ============================================================================
// Billing Summary
// ============================================================================

export const getMonthlySummary = async (
  username: string,
  billingMonth: string
): Promise<BillingSummary> => {
  const res = await axios.get(`${API_BASE}/summary/${username}`, {
    params: { billing_month: billingMonth },
  });
  return res.data.summary;
};

// ============================================================================
// Dashboard
// ============================================================================

export const getDashboardData = async (): Promise<DashboardDataPoint[]> => {
  const res = await axios.get(`${API_BASE}/dashboard`);
  return res.data.data;
};

// ============================================================================
// Admin Operations
// ============================================================================

export const resetUserUsage = async (
  username: string,
  billingMonth: string
): Promise<void> => {
  await axios.post(`${API_BASE}/reset/${username}`, {
    billing_month: billingMonth,
  });
};
