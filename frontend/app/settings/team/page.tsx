'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { AppShell } from '@/components/AppShell';
import Link from 'next/link';

export default function TeamSettingsPage() {
    const [members, setMembers] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [inviteEmail, setInviteEmail] = useState('');
    const [inviteRole, setInviteRole] = useState('MEMBER');
    const [inviteLink, setInviteLink] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        loadTeam();
    }, []);

    const loadTeam = () => {
        api.fetchTeam()
            .then(setMembers)
            .catch(e => console.error(e))
            .finally(() => setLoading(false));
    };

    const handleInvite = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        setInviteLink(null);
        try {
            const res = await api.inviteMember(inviteEmail, inviteRole);
            setInviteLink(res.link);
            setInviteEmail('');
        } catch (e: any) {
            setError("Failed to invite member. Ensure you are an Admin.");
        }
    };

    const handleRemove = async (id: number) => {
        if (!confirm('Are you sure you want to remove this member?')) return;
        try {
            await api.removeMember(id);
            setMembers(members.filter(m => m.id !== id));
        } catch (e) {
            setError('Failed to remove member.');
        }
    };

    return (
        <AppShell>
        <main className="p-8">
            <div className="max-w-4xl mx-auto">

                <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden mb-8">
                    <div className="px-6 py-4 border-b bg-gray-50 flex justify-between items-center">
                        <div>
                            <h1 className="text-xl font-bold text-gray-900">Team Members</h1>
                            <p className="text-sm text-gray-500">Manage who has access to your organization.</p>
                        </div>
                    </div>

                    <table className="w-full text-sm text-left text-gray-600">
                        <thead className="text-xs text-gray-500 uppercase bg-gray-50 border-b">
                            <tr>
                                <th className="px-6 py-3">Name</th>
                                <th className="px-6 py-3">Email</th>
                                <th className="px-6 py-3">Role</th>
                                <th className="px-6 py-3 text-right">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {loading ? (
                                <tr><td colSpan={4} className="px-6 py-8 text-center">Loading...</td></tr>
                            ) : members.map((member) => (
                                <tr key={member.id} className="bg-white border-b hover:bg-gray-50">
                                    <td className="px-6 py-3 font-medium text-gray-900">{member.full_name || 'N/A'}</td>
                                    <td className="px-6 py-3">{member.email}</td>
                                    <td className="px-6 py-3">
                                        <span className={`px-2 py-1 rounded text-xs font-medium ${member.role === 'ADMIN' ? 'bg-purple-100 text-purple-700' : 'bg-gray-100 text-gray-600'
                                            }`}>
                                            {member.role || 'MEMBER'}
                                        </span>
                                    </td>
                                    <td className="px-6 py-3 text-right">
                                        <button
                                            onClick={() => handleRemove(member.id)}
                                            className="text-red-600 hover:text-red-900 text-xs font-medium"
                                        >
                                            Remove
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>

                <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6">
                    <h2 className="text-lg font-bold text-gray-900 mb-4">Invite New Member</h2>

                    <form onSubmit={handleInvite} className="flex gap-4 items-end">
                        <div className="flex-1">
                            <label className="block text-sm font-medium text-gray-700 mb-1">Email Address</label>
                            <input
                                type="email"
                                required
                                value={inviteEmail}
                                onChange={e => setInviteEmail(e.target.value)}
                                className="w-full rounded-md border-gray-300 shadow-sm focus:border-purple-500 focus:ring-purple-500 sm:text-sm px-3 py-2 border"
                                placeholder="colleague@example.com"
                            />
                        </div>
                        <div className="w-40">
                            <label className="block text-sm font-medium text-gray-700 mb-1">Role</label>
                            <select
                                value={inviteRole}
                                onChange={e => setInviteRole(e.target.value)}
                                className="w-full rounded-md border-gray-300 shadow-sm focus:border-purple-500 focus:ring-purple-500 sm:text-sm px-3 py-2 border"
                            >
                                <option value="MEMBER">Member</option>
                                <option value="ADMIN">Admin</option>
                                <option value="VIEWER">Viewer</option>
                            </select>
                        </div>
                        <button
                            type="submit"
                            className="bg-purple-600 text-white px-4 py-2 rounded-md hover:bg-purple-700 text-sm font-medium shadow-sm"
                        >
                            Send Invite
                        </button>
                    </form>

                    {error && (
                        <div className="mt-4 p-3 bg-red-50 text-red-700 text-sm rounded-md border border-red-200">
                            {error}
                        </div>
                    )}

                    {inviteLink && (
                        <div className="mt-6 p-4 bg-green-50 rounded-md border border-green-200">
                            <h3 className="text-sm font-bold text-green-800 mb-2">Invitation Created!</h3>
                            <p className="text-sm text-green-700 mb-2">Share this link with your teammate:</p>
                            <div className="bg-white p-2 rounded border border-green-200 font-mono text-xs text-gray-600 break-all">
                                {inviteLink}
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </main>
        </AppShell>
    );
}
