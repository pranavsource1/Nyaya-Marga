'use client';

import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { UserSummary } from '@/lib/types';
import { Loader2, ShieldCheck, Users } from 'lucide-react';

function formatDate(value: string | null) {
  if (!value) return '-';
  return new Date(value).toLocaleDateString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  });
}

function formatRole(role: string) {
  return role.replace(/_/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase());
}

export default function UsersPage() {
  const { data = [], isLoading } = useQuery({
    queryKey: ['users'],
    queryFn: () => api.listUsers(),
    refetchInterval: 60000,
  });

  return (
    <div className="max-w-6xl mx-auto space-y-6 pb-12">
      <section>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Users & Roles</h1>
        <p className="text-sm text-slate-500 mt-1">Active backend user accounts and authorization roles.</p>
      </section>

      <section className="bg-white rounded-lg border border-slate-200 overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-100 flex items-center gap-2">
          <Users className="w-4 h-4 text-gov-700" />
          <h2 className="text-sm font-bold text-slate-800">Backend Users</h2>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50/80">
                <th className="px-5 py-3 text-[11px] font-bold text-slate-500 uppercase tracking-wider">Officer</th>
                <th className="px-5 py-3 text-[11px] font-bold text-slate-500 uppercase tracking-wider">Department</th>
                <th className="px-5 py-3 text-[11px] font-bold text-slate-500 uppercase tracking-wider">Role</th>
                <th className="px-5 py-3 text-[11px] font-bold text-slate-500 uppercase tracking-wider">Status</th>
                <th className="px-5 py-3 text-[11px] font-bold text-slate-500 uppercase tracking-wider">Last Login</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {isLoading ? (
                <tr>
                  <td colSpan={5} className="px-5 py-12 text-center text-sm text-slate-500">
                    <span className="inline-flex items-center gap-2">
                      <Loader2 className="w-5 h-5 animate-spin text-gov-700" />
                      Loading users...
                    </span>
                  </td>
                </tr>
              ) : data.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-5 py-12 text-center text-sm text-slate-500">
                    No users were returned by the backend.
                  </td>
                </tr>
              ) : (
                data.map((user: UserSummary) => (
                  <tr key={user.id} className="hover:bg-slate-50">
                    <td className="px-5 py-3.5">
                      <div className="text-sm font-semibold text-slate-800">{user.full_name}</div>
                      <div className="text-xs text-slate-500">{user.email}</div>
                    </td>
                    <td className="px-5 py-3.5 text-sm text-slate-600">{user.department}</td>
                    <td className="px-5 py-3.5">
                      <span className="inline-flex items-center gap-1.5 rounded-md bg-gov-50 px-2 py-0.5 text-[11px] font-bold text-gov-700 uppercase tracking-wide ring-1 ring-gov-100">
                        <ShieldCheck className="w-3 h-3" />
                        {formatRole(user.role)}
                      </span>
                    </td>
                    <td className="px-5 py-3.5">
                      <span
                        className={`inline-flex rounded-md px-2 py-0.5 text-[11px] font-bold uppercase tracking-wide ${
                          user.is_active
                            ? 'bg-ka-green-50 text-ka-green-700 ring-1 ring-ka-green-200'
                            : 'bg-ka-crimson-50 text-ka-crimson-700 ring-1 ring-ka-crimson-200'
                        }`}
                      >
                        {user.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 text-sm text-slate-600">{formatDate(user.last_login_at)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
