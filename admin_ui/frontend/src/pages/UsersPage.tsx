import React, { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Building2, ServerCog, ShieldAlert, UserPlus, RefreshCw, Search, UserX, Trash2, KeyRound } from 'lucide-react';

import { useAuth } from '../auth/AuthContext';
import { ConfigSection } from '../components/ui/ConfigSection';
import { ConfigCard } from '../components/ui/ConfigCard';

type UserRole = 'super_admin' | 'admin' | 'reseller_admin' | 'end_user' | 'readonly_user';
type UserStatus = 'active' | 'disabled';

interface ManagedUser {
    user_id: string;
    username: string;
    email: string;
    role: UserRole;
    status: UserStatus;
    tenant_id?: string;
    workspace_id?: string;
    assigned_agent_id?: string | null;
    department?: string | null;
    created_at?: string | null;
    last_login?: string | null;
}

interface CreateUserForm {
    account_scope: 'workspace_user' | 'reseller_tenant';
    username: string;
    email: string;
    password: string;
    role: UserRole;
    company_name: string;
    slug: string;
    domain: string;
    subscription_plan: 'starter' | 'growth' | 'enterprise';
    max_users: string;
    max_agents: string;
    max_calls_per_day: string;
    api_quota: string;
    asterisk_host: string;
    sip_trunk: string;
    did_number: string;
    sip_username: string;
    sip_transport: 'udp' | 'tcp' | 'tls';
    assigned_agent_id: string;
    department: string;
    access_level: 'full' | 'standard' | 'restricted';
}

const initialForm: CreateUserForm = {
    account_scope: 'workspace_user',
    username: '',
    email: '',
    password: '',
    role: 'end_user',
    company_name: '',
    slug: '',
    domain: '',
    subscription_plan: 'starter',
    max_users: '5',
    max_agents: '2',
    max_calls_per_day: '100',
    api_quota: '1000',
    asterisk_host: '',
    sip_trunk: '',
    did_number: '',
    sip_username: '',
    sip_transport: 'udp',
    assigned_agent_id: '',
    department: '',
    access_level: 'standard',
};

const permissionsByAccess: Record<CreateUserForm['access_level'], string[]> = {
    full: ['manage_workspace', 'manage_users', 'configure_providers', 'view_billing', 'manage_agents'],
    standard: ['consume_voice', 'view_call_history', 'view_assigned_agents'],
    restricted: ['consume_voice'],
};

const UsersPage: React.FC = () => {
    const { user } = useAuth();
    const [users, setUsers] = useState<ManagedUser[]>([]);
    const [loading, setLoading] = useState(true);
    const [creating, setCreating] = useState(false);
    const [search, setSearch] = useState('');
    const [roleFilter, setRoleFilter] = useState<'all' | UserRole>('all');
    const [statusFilter, setStatusFilter] = useState<'all' | UserStatus>('all');
    const [form, setForm] = useState<CreateUserForm>(initialForm);

    const isAdmin = user?.role === 'super_admin' || user?.role === 'admin' || user?.username === 'admin';
    const isSuperAdmin = user?.role === 'super_admin' || user?.username === 'admin';
    const isResellerTenant = form.account_scope === 'reseller_tenant';

    const loadUsers = async () => {
        try {
            setLoading(true);
            const response = await axios.get('/api/users/list');
            const list = Array.isArray(response.data?.users) ? response.data.users : [];
            setUsers(list);
        } catch (error: any) {
            toast.error(error?.response?.data?.detail || 'Failed to load users');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (isAdmin) {
            loadUsers();
        } else {
            setLoading(false);
        }
    }, [isAdmin]);

    const filteredUsers = useMemo(() => {
        return users.filter((entry) => {
            const searchQuery = search.trim().toLowerCase();
            const matchesSearch = !searchQuery
                || entry.username.toLowerCase().includes(searchQuery)
                || entry.email.toLowerCase().includes(searchQuery)
                || (entry.department || '').toLowerCase().includes(searchQuery);
            const matchesRole = roleFilter === 'all' || entry.role === roleFilter;
            const matchesStatus = statusFilter === 'all' || entry.status === statusFilter;
            return matchesSearch && matchesRole && matchesStatus;
        });
    }, [users, search, roleFilter, statusFilter]);

    const onCreateUser = async (event: React.FormEvent) => {
        event.preventDefault();
        if (!form.username || !form.email || !form.password) {
            toast.error('Username, email, and password are required');
            return;
        }
        if (isResellerTenant && !form.company_name.trim()) {
            toast.error('Company name is required for a separate reseller tenant');
            return;
        }
        setCreating(true);
        try {
            const numberOrNull = (value: string) => {
                const trimmed = value.trim();
                if (!trimmed) return null;
                const parsed = Number(trimmed);
                return Number.isFinite(parsed) ? parsed : null;
            };
            await axios.post('/api/users/create', {
                username: form.username.trim(),
                email: form.email.trim(),
                password: form.password,
                role: form.role,
                provision_separate_tenant: isResellerTenant,
                company_name: isResellerTenant ? form.company_name.trim() : null,
                slug: isResellerTenant ? form.slug.trim() || null : null,
                domain: isResellerTenant ? form.domain.trim() || null : null,
                subscription_plan: form.subscription_plan,
                max_users: numberOrNull(form.max_users),
                max_agents: numberOrNull(form.max_agents),
                max_calls_per_day: numberOrNull(form.max_calls_per_day),
                api_quota: numberOrNull(form.api_quota),
                asterisk_host: isResellerTenant ? form.asterisk_host.trim() || null : null,
                sip_trunk: isResellerTenant ? form.sip_trunk.trim() || null : null,
                did_number: isResellerTenant ? form.did_number.trim() || null : null,
                sip_username: isResellerTenant ? form.sip_username.trim() || null : null,
                sip_transport: form.sip_transport,
                assigned_agent_id: form.assigned_agent_id || null,
                department: form.department || null,
                permissions: permissionsByAccess[form.access_level],
            });
            toast.success(isResellerTenant ? 'Reseller tenant created successfully' : 'User created successfully');
            setForm(initialForm);
            await loadUsers();
        } catch (error: any) {
            toast.error(error?.response?.data?.detail || 'Failed to create user');
        } finally {
            setCreating(false);
        }
    };

    const onDisableUser = async (username: string) => {
        try {
            await axios.post('/api/users/disable', { username });
            toast.success(`Disabled ${username}`);
            await loadUsers();
        } catch (error: any) {
            toast.error(error?.response?.data?.detail || 'Failed to disable user');
        }
    };

    const onDeleteUser = async (username: string) => {
        const confirmed = window.confirm(`Delete user "${username}"? This action cannot be undone.`);
        if (!confirmed) return;
        try {
            await axios.delete('/api/users/delete', { data: { username } });
            toast.success(`Deleted ${username}`);
            await loadUsers();
        } catch (error: any) {
            toast.error(error?.response?.data?.detail || 'Failed to delete user');
        }
    };

    const onResetPassword = async (username: string) => {
        const newPassword = window.prompt(`Enter new password for ${username}`);
        if (!newPassword) return;
        try {
            await axios.post('/api/users/reset-password', { username, password: newPassword });
            toast.success(`Password reset for ${username}`);
        } catch (error: any) {
            toast.error(error?.response?.data?.detail || 'Failed to reset password');
        }
    };

    if (!isAdmin) {
        return (
            <div className="rounded-lg border border-destructive/40 bg-destructive/5 p-6">
                <div className="flex items-start gap-3">
                    <ShieldAlert className="w-5 h-5 text-destructive mt-0.5" />
                    <div>
                        <h2 className="text-lg font-semibold">Access Denied</h2>
                        <p className="text-sm text-muted-foreground mt-1">
                            Only tenant administrators can manage users.
                        </p>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <ConfigSection
                title="Users & Reseller Accounts"
                description="Create workspace users or provision a separate reseller/customer tenant under the platform admin."
            >
                <ConfigCard className="p-4">
                    <form onSubmit={onCreateUser} className="space-y-4">
                        <div className="flex items-center gap-2 mb-2">
                            <UserPlus className="w-4 h-4 text-primary" />
                            <h3 className="text-sm font-semibold">Create Account</h3>
                        </div>
                        {isSuperAdmin && (
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                <label className={`flex items-start gap-3 p-3 rounded-md border cursor-pointer ${!isResellerTenant ? 'border-primary bg-primary/5' : 'border-border hover:bg-accent/50'}`}>
                                    <input
                                        type="radio"
                                        className="mt-1"
                                        checked={!isResellerTenant}
                                        onChange={() => setForm((prev) => ({ ...prev, account_scope: 'workspace_user', role: 'end_user' }))}
                                    />
                                    <UserPlus className="w-4 h-4 mt-0.5 text-muted-foreground" />
                                    <span>
                                        <span className="block text-sm font-medium">Workspace User</span>
                                        <span className="block text-xs text-muted-foreground">Create a user inside the current tenant.</span>
                                    </span>
                                </label>
                                <label className={`flex items-start gap-3 p-3 rounded-md border cursor-pointer ${isResellerTenant ? 'border-primary bg-primary/5' : 'border-border hover:bg-accent/50'}`}>
                                    <input
                                        type="radio"
                                        className="mt-1"
                                        checked={isResellerTenant}
                                        onChange={() => setForm((prev) => ({ ...prev, account_scope: 'reseller_tenant', role: 'admin', access_level: 'full' }))}
                                    />
                                    <Building2 className="w-4 h-4 mt-0.5 text-muted-foreground" />
                                    <span>
                                        <span className="block text-sm font-medium">Separate Reseller Tenant</span>
                                        <span className="block text-xs text-muted-foreground">Provision an isolated tenant owner with limits and Asterisk setup data.</span>
                                    </span>
                                </label>
                            </div>
                        )}
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                            {isResellerTenant && (
                                <>
                                    <div>
                                        <label className="block text-xs font-medium text-muted-foreground mb-1">Company Name</label>
                                        <input
                                            className="w-full px-3 py-2 border border-input rounded-md bg-background text-sm"
                                            value={form.company_name}
                                            onChange={(event) => setForm((prev) => ({ ...prev, company_name: event.target.value }))}
                                            placeholder="Acme Voice Agency"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-xs font-medium text-muted-foreground mb-1">Tenant Slug</label>
                                        <input
                                            className="w-full px-3 py-2 border border-input rounded-md bg-background text-sm"
                                            value={form.slug}
                                            onChange={(event) => setForm((prev) => ({ ...prev, slug: event.target.value }))}
                                            placeholder="acme-voice"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-xs font-medium text-muted-foreground mb-1">Custom Domain</label>
                                        <input
                                            className="w-full px-3 py-2 border border-input rounded-md bg-background text-sm"
                                            value={form.domain}
                                            onChange={(event) => setForm((prev) => ({ ...prev, domain: event.target.value }))}
                                            placeholder="voice.acme.com"
                                        />
                                    </div>
                                </>
                            )}
                            <div>
                                <label className="block text-xs font-medium text-muted-foreground mb-1">Username</label>
                                <input
                                    className="w-full px-3 py-2 border border-input rounded-md bg-background text-sm"
                                    value={form.username}
                                    onChange={(event) => setForm((prev) => ({ ...prev, username: event.target.value }))}
                                    placeholder="john.doe"
                                />
                            </div>
                            <div>
                                <label className="block text-xs font-medium text-muted-foreground mb-1">Email</label>
                                <input
                                    type="email"
                                    className="w-full px-3 py-2 border border-input rounded-md bg-background text-sm"
                                    value={form.email}
                                    onChange={(event) => setForm((prev) => ({ ...prev, email: event.target.value }))}
                                    placeholder="john@company.com"
                                />
                            </div>
                            <div>
                                <label className="block text-xs font-medium text-muted-foreground mb-1">Password</label>
                                <input
                                    type="password"
                                    className="w-full px-3 py-2 border border-input rounded-md bg-background text-sm"
                                    value={form.password}
                                    onChange={(event) => setForm((prev) => ({ ...prev, password: event.target.value }))}
                                    placeholder="Temporary password"
                                />
                            </div>
                            <div>
                                <label className="block text-xs font-medium text-muted-foreground mb-1">Role</label>
                                <select
                                    className="w-full px-3 py-2 border border-input rounded-md bg-background text-sm"
                                    value={form.role}
                                    onChange={(event) => setForm((prev) => ({ ...prev, role: event.target.value as UserRole }))}
                                >
                                    {!isResellerTenant && <option value="end_user">End User</option>}
                                    {!isResellerTenant && <option value="readonly_user">Read-only User</option>}
                                    {!isResellerTenant && <option value="reseller_admin">Reseller Admin</option>}
                                    <option value="admin">Admin</option>
                                    {isSuperAdmin && <option value="super_admin">Super Admin</option>}
                                </select>
                            </div>
                            <div>
                                <label className="block text-xs font-medium text-muted-foreground mb-1">Assign Agent</label>
                                <input
                                    className="w-full px-3 py-2 border border-input rounded-md bg-background text-sm"
                                    value={form.assigned_agent_id}
                                    onChange={(event) => setForm((prev) => ({ ...prev, assigned_agent_id: event.target.value }))}
                                    placeholder="sales-agent"
                                />
                            </div>
                            <div>
                                <label className="block text-xs font-medium text-muted-foreground mb-1">Department</label>
                                <input
                                    className="w-full px-3 py-2 border border-input rounded-md bg-background text-sm"
                                    value={form.department}
                                    onChange={(event) => setForm((prev) => ({ ...prev, department: event.target.value }))}
                                    placeholder="Support"
                                />
                            </div>
                            <div>
                                <label className="block text-xs font-medium text-muted-foreground mb-1">Access Level</label>
                                <select
                                    className="w-full px-3 py-2 border border-input rounded-md bg-background text-sm"
                                    value={form.access_level}
                                    onChange={(event) => setForm((prev) => ({ ...prev, access_level: event.target.value as CreateUserForm['access_level'] }))}
                                >
                                    <option value="full">Full</option>
                                    <option value="standard">Standard</option>
                                    <option value="restricted">Restricted</option>
                                </select>
                            </div>
                        </div>
                        {isResellerTenant && (
                            <>
                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 pt-2">
                                    <div>
                                        <label className="block text-xs font-medium text-muted-foreground mb-1">Plan</label>
                                        <select
                                            className="w-full px-3 py-2 border border-input rounded-md bg-background text-sm"
                                            value={form.subscription_plan}
                                            onChange={(event) => setForm((prev) => ({ ...prev, subscription_plan: event.target.value as CreateUserForm['subscription_plan'] }))}
                                        >
                                            <option value="starter">Starter</option>
                                            <option value="growth">Growth</option>
                                            <option value="enterprise">Enterprise</option>
                                        </select>
                                    </div>
                                    <div>
                                        <label className="block text-xs font-medium text-muted-foreground mb-1">Max Users</label>
                                        <input className="w-full px-3 py-2 border border-input rounded-md bg-background text-sm" value={form.max_users} onChange={(event) => setForm((prev) => ({ ...prev, max_users: event.target.value }))} />
                                    </div>
                                    <div>
                                        <label className="block text-xs font-medium text-muted-foreground mb-1">Max Agents</label>
                                        <input className="w-full px-3 py-2 border border-input rounded-md bg-background text-sm" value={form.max_agents} onChange={(event) => setForm((prev) => ({ ...prev, max_agents: event.target.value }))} />
                                    </div>
                                    <div>
                                        <label className="block text-xs font-medium text-muted-foreground mb-1">Daily Calls</label>
                                        <input className="w-full px-3 py-2 border border-input rounded-md bg-background text-sm" value={form.max_calls_per_day} onChange={(event) => setForm((prev) => ({ ...prev, max_calls_per_day: event.target.value }))} />
                                    </div>
                                </div>
                                <div className="rounded-md border border-border p-3">
                                    <div className="flex items-center gap-2 mb-3">
                                        <ServerCog className="w-4 h-4 text-primary" />
                                        <h4 className="text-sm font-semibold">Asterisk Server For This Tenant</h4>
                                    </div>
                                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                                        <div>
                                            <label className="block text-xs font-medium text-muted-foreground mb-1">Asterisk Host</label>
                                            <input className="w-full px-3 py-2 border border-input rounded-md bg-background text-sm" value={form.asterisk_host} onChange={(event) => setForm((prev) => ({ ...prev, asterisk_host: event.target.value }))} placeholder="pbx.customer.com" />
                                        </div>
                                        <div>
                                            <label className="block text-xs font-medium text-muted-foreground mb-1">SIP Trunk</label>
                                            <input className="w-full px-3 py-2 border border-input rounded-md bg-background text-sm" value={form.sip_trunk} onChange={(event) => setForm((prev) => ({ ...prev, sip_trunk: event.target.value }))} placeholder="trunk_customer" />
                                        </div>
                                        <div>
                                            <label className="block text-xs font-medium text-muted-foreground mb-1">DID Number</label>
                                            <input className="w-full px-3 py-2 border border-input rounded-md bg-background text-sm" value={form.did_number} onChange={(event) => setForm((prev) => ({ ...prev, did_number: event.target.value }))} placeholder="+15551234567" />
                                        </div>
                                        <div>
                                            <label className="block text-xs font-medium text-muted-foreground mb-1">SIP Username</label>
                                            <input className="w-full px-3 py-2 border border-input rounded-md bg-background text-sm" value={form.sip_username} onChange={(event) => setForm((prev) => ({ ...prev, sip_username: event.target.value }))} placeholder="tenant_sip_user" />
                                        </div>
                                        <div>
                                            <label className="block text-xs font-medium text-muted-foreground mb-1">Transport</label>
                                            <select className="w-full px-3 py-2 border border-input rounded-md bg-background text-sm" value={form.sip_transport} onChange={(event) => setForm((prev) => ({ ...prev, sip_transport: event.target.value as CreateUserForm['sip_transport'] }))}>
                                                <option value="udp">UDP</option>
                                                <option value="tcp">TCP</option>
                                                <option value="tls">TLS</option>
                                            </select>
                                        </div>
                                        <div>
                                            <label className="block text-xs font-medium text-muted-foreground mb-1">API Quota</label>
                                            <input className="w-full px-3 py-2 border border-input rounded-md bg-background text-sm" value={form.api_quota} onChange={(event) => setForm((prev) => ({ ...prev, api_quota: event.target.value }))} />
                                        </div>
                                    </div>
                                </div>
                            </>
                        )}
                        <div className="flex justify-end">
                            <button
                                type="submit"
                                disabled={creating}
                                className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 disabled:opacity-60"
                            >
                                {creating ? <RefreshCw className="w-4 h-4 animate-spin" /> : <UserPlus className="w-4 h-4" />}
                                {isResellerTenant ? 'Create Reseller' : 'Create User'}
                            </button>
                        </div>
                    </form>
                </ConfigCard>
            </ConfigSection>

            <ConfigSection title="Users" description="Search, filter, and manage workspace users.">
                <ConfigCard className="p-4">
                    <div className="flex flex-col md:flex-row gap-3 md:items-center md:justify-between mb-4">
                        <div className="flex items-center gap-2 w-full md:w-auto">
                            <div className="relative w-full md:w-80">
                                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                                <input
                                    value={search}
                                    onChange={(event) => setSearch(event.target.value)}
                                    placeholder="Search users"
                                    className="w-full pl-9 pr-3 py-2 border border-input rounded-md bg-background text-sm"
                                />
                            </div>
                            <select
                                value={roleFilter}
                                onChange={(event) => setRoleFilter(event.target.value as 'all' | UserRole)}
                                className="px-3 py-2 border border-input rounded-md bg-background text-sm"
                            >
                                <option value="all">All Roles</option>
                                <option value="super_admin">Super Admin</option>
                                <option value="admin">Admin</option>
                                <option value="reseller_admin">Reseller Admin</option>
                                <option value="end_user">End User</option>
                                <option value="readonly_user">Read-only User</option>
                            </select>
                            <select
                                value={statusFilter}
                                onChange={(event) => setStatusFilter(event.target.value as 'all' | UserStatus)}
                                className="px-3 py-2 border border-input rounded-md bg-background text-sm"
                            >
                                <option value="all">All Status</option>
                                <option value="active">Active</option>
                                <option value="disabled">Disabled</option>
                            </select>
                        </div>
                        <button
                            onClick={loadUsers}
                            className="inline-flex items-center gap-2 px-3 py-2 rounded-md border border-input text-sm hover:bg-accent"
                        >
                            <RefreshCw className="w-4 h-4" />
                            Refresh
                        </button>
                    </div>

                    <div className="overflow-x-auto border border-border rounded-md">
                        <table className="w-full text-sm">
                            <thead className="bg-accent/50 text-left">
                                <tr>
                                    <th className="px-3 py-2 font-medium">Name</th>
                                    <th className="px-3 py-2 font-medium">Email</th>
                                    <th className="px-3 py-2 font-medium">Tenant</th>
                                    <th className="px-3 py-2 font-medium">Role</th>
                                    <th className="px-3 py-2 font-medium">Assigned Agent</th>
                                    <th className="px-3 py-2 font-medium">Status</th>
                                    <th className="px-3 py-2 font-medium">Created</th>
                                    <th className="px-3 py-2 font-medium">Last Login</th>
                                    <th className="px-3 py-2 font-medium text-right">Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {loading && (
                                    <tr>
                                        <td colSpan={9} className="px-3 py-8 text-center text-muted-foreground">
                                            Loading users...
                                        </td>
                                    </tr>
                                )}
                                {!loading && filteredUsers.length === 0 && (
                                    <tr>
                                        <td colSpan={9} className="px-3 py-8 text-center text-muted-foreground">
                                            No users found for the current filters.
                                        </td>
                                    </tr>
                                )}
                                {!loading && filteredUsers.map((entry) => (
                                    <tr key={entry.user_id} className="border-t border-border">
                                        <td className="px-3 py-2">{entry.username}</td>
                                        <td className="px-3 py-2">{entry.email}</td>
                                        <td className="px-3 py-2">{entry.tenant_id || '-'}</td>
                                        <td className="px-3 py-2">{entry.role}</td>
                                        <td className="px-3 py-2">{entry.assigned_agent_id || '-'}</td>
                                        <td className="px-3 py-2">
                                            <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${entry.status === 'active' ? 'bg-green-500/15 text-green-700 dark:text-green-400' : 'bg-destructive/15 text-destructive'}`}>
                                                {entry.status}
                                            </span>
                                        </td>
                                        <td className="px-3 py-2">{entry.created_at ? new Date(entry.created_at).toLocaleDateString() : '-'}</td>
                                        <td className="px-3 py-2">{entry.last_login ? new Date(entry.last_login).toLocaleString() : '-'}</td>
                                        <td className="px-3 py-2">
                                            <div className="flex items-center justify-end gap-1">
                                                <button
                                                    onClick={() => onResetPassword(entry.username)}
                                                    className="p-1.5 rounded hover:bg-accent text-muted-foreground hover:text-foreground"
                                                    title="Reset Password"
                                                >
                                                    <KeyRound className="w-4 h-4" />
                                                </button>
                                                {entry.status === 'active' && (
                                                    <button
                                                        onClick={() => onDisableUser(entry.username)}
                                                        className="p-1.5 rounded hover:bg-accent text-amber-600 hover:text-amber-700"
                                                        title="Suspend"
                                                    >
                                                        <UserX className="w-4 h-4" />
                                                    </button>
                                                )}
                                                <button
                                                    onClick={() => onDeleteUser(entry.username)}
                                                    className="p-1.5 rounded hover:bg-destructive/15 text-destructive"
                                                    title="Delete"
                                                >
                                                    <Trash2 className="w-4 h-4" />
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </ConfigCard>
            </ConfigSection>
        </div>
    );
};

export default UsersPage;
