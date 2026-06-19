"use client";

import Link from "next/link";
import { useAuth } from "@/app/context/AuthContext";

export default function LandingPage() {
    const { user } = useAuth();

    return (
        <div className="min-h-screen bg-white">
            {/* Navbar */}
            <nav className="border-b border-gray-100">
                <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
                    <div className="font-bold text-xl text-indigo-600 flex items-center gap-2">
                        <span>⚡</span> SparqAI
                    </div>
                    <div className="flex items-center gap-4">
                        {user ? (
                            <Link
                                href="/dashboard"
                                className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-full hover:bg-indigo-700 transition"
                            >
                                Go to Dashboard
                            </Link>
                        ) : (
                            <>
                                <Link
                                    href="/login"
                                    className="text-sm font-medium text-gray-600 hover:text-gray-900"
                                >
                                    Log in
                                </Link>
                                <Link
                                    href="/register"
                                    className="px-4 py-2 bg-black text-white text-sm font-medium rounded-full hover:bg-gray-800 transition"
                                >
                                    Sign up
                                </Link>
                            </>
                        )}
                    </div>
                </div>
            </nav>

            {/* Hero Section */}
            <main>
                <div className="max-w-7xl mx-auto px-6 py-20 lg:py-32 text-center">
                    <h1 className="text-5xl lg:text-7xl font-extrabold text-gray-900 tracking-tight mb-8">
                        Stop Guessing.<br />
                        <span className="text-indigo-600">Start Knowing.</span>
                    </h1>
                    <p className="text-xl text-gray-500 max-w-2xl mx-auto mb-10 leading-relaxed">
                        The only ROI attribution platform that tracks every GTM investment—from hires to software to ads—and tells you what’s actually driving revenue.
                    </p>
                    <div className="flex flex-col sm:flex-row gap-4 justify-center mb-16">
                        <Link
                            href="/register"
                            className="px-8 py-4 bg-indigo-600 text-white text-lg font-bold rounded-full hover:bg-indigo-700 shadow-lg hover:shadow-xl transition transform hover:-translate-y-1"
                        >
                            Start Free Trial
                        </Link>
                        <Link
                            href="#features"
                            className="px-8 py-4 bg-white text-gray-700 border border-gray-200 text-lg font-bold rounded-full hover:bg-gray-50 transition"
                        >
                            See How It Works
                        </Link>
                    </div>

                    {/* Dashboard Preview */}
                    <div className="relative rounded-2xl border border-gray-200 shadow-2xl overflow-hidden max-w-5xl mx-auto bg-gray-50 p-2">
                        <div className="bg-white rounded-xl overflow-hidden border border-gray-100">
                            {/* Placeholder for screenshot or mock UI */}
                            <div className="p-8 grid grid-cols-1 md:grid-cols-3 gap-8 text-left">
                                <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-100">
                                    <div className="text-sm text-gray-500 mb-1">Total Invested</div>
                                    <div className="text-2xl font-bold text-gray-900">$142,500</div>
                                </div>
                                <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-100">
                                    <div className="text-sm text-gray-500 mb-1">Attributed Revenue</div>
                                    <div className="text-2xl font-bold text-green-600">$845,200</div>
                                </div>
                                <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-100">
                                    <div className="text-sm text-gray-500 mb-1">ROI Multiple</div>
                                    <div className="text-2xl font-bold text-green-600">5.93x</div>
                                </div>
                            </div>
                            <div className="px-8 pb-8">
                                <table className="w-full text-left text-sm text-gray-600">
                                    <thead className="bg-gray-50 text-xs uppercase text-gray-400 font-semibold">
                                        <tr>
                                            <th className="p-3">Investment</th>
                                            <th className="p-3">Type</th>
                                            <th className="p-3">Cost</th>
                                            <th className="p-3">Revenue Impact</th>
                                            <th className="p-3">ROI</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-gray-100">
                                        <tr>
                                            <td className="p-3 font-medium text-gray-900">LinkedIn Q1 Campaign</td>
                                            <td className="p-3"><span className="bg-blue-100 text-blue-800 px-2 py-0.5 rounded-full text-xs">Ad Campaign</span></td>
                                            <td className="p-3">$5,000</td>
                                            <td className="p-3 font-medium text-green-600">$42,000</td>
                                            <td className="p-3 font-bold text-green-600">8.4x</td>
                                        </tr>
                                        <tr>
                                            <td className="p-3 font-medium text-gray-900">Senior AE (Sarah)</td>
                                            <td className="p-3"><span className="bg-purple-100 text-purple-800 px-2 py-0.5 rounded-full text-xs">Hire</span></td>
                                            <td className="p-3">$8,500/mo</td>
                                            <td className="p-3 font-medium text-green-600">$125,000</td>
                                            <td className="p-3 font-bold text-green-600">14.7x</td>
                                        </tr>
                                        <tr>
                                            <td className="p-3 font-medium text-gray-900">ZoomInfo Subscription</td>
                                            <td className="p-3"><span className="bg-yellow-100 text-yellow-800 px-2 py-0.5 rounded-full text-xs">Tool</span></td>
                                            <td className="p-3">$2,000/mo</td>
                                            <td className="p-3 font-medium text-red-600">$0</td>
                                            <td className="p-3 font-bold text-red-600">0.0x</td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
            </main>

            {/* Features Section */}
            <section id="features" className="py-24 bg-gray-50">
                <div className="max-w-7xl mx-auto px-6">
                    <div className="text-center mb-16">
                        <h2 className="text-3xl font-bold text-gray-900">Everything you need to justify your spend.</h2>
                        <p className="text-gray-500 mt-4 max-w-2xl mx-auto">
                            Most tools only track ads. SparqAI tracks everything—from the headcount you approve to the software you buy.
                        </p>
                    </div>
                    <div className="grid md:grid-cols-3 gap-8">
                        <div className="bg-white p-8 rounded-xl shadow-sm border border-gray-100">
                            <div className="w-12 h-12 bg-indigo-100 rounded-lg flex items-center justify-center text-indigo-600 mb-6 text-2xl">📊</div>
                            <h3 className="text-xl font-bold text-gray-900 mb-2">Unified Attribution</h3>
                            <p className="text-gray-500">
                                Connect CRM revenue data to manual decision entries. See exactly which decisions led to which closed deals.
                            </p>
                        </div>
                        <div className="bg-white p-8 rounded-xl shadow-sm border border-gray-100">
                            <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center text-purple-600 mb-6 text-2xl">🤖</div>
                            <h3 className="text-xl font-bold text-gray-900 mb-2">AI Insights</h3>
                            <p className="text-gray-500">
                                Our AI analyzes your historical data to recommend where to double down and what to cut immediately.
                            </p>
                        </div>
                        <div className="bg-white p-8 rounded-xl shadow-sm border border-gray-100">
                            <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center text-blue-600 mb-6 text-2xl">🔌</div>
                            <h3 className="text-xl font-bold text-gray-900 mb-2">HubSpot & Salesforce</h3>
                            <p className="text-gray-500">
                                One-click integration with your existing CRM. We pull deal data automatically so you don&apos;t have to.
                            </p>
                        </div>
                    </div>
                </div>
            </section>

            {/* Pricing Section */}
            <section className="py-24 bg-white border-b border-gray-100">
                <div className="max-w-7xl mx-auto px-6">
                    <div className="text-center mb-16">
                        <h2 className="text-3xl font-bold text-gray-900">Simple, transparent pricing.</h2>
                        <p className="text-gray-500 mt-4">Start for free, upgrade as you grow.</p>
                    </div>
                    <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
                        {/* Free */}
                        <div className="p-8 rounded-2xl border border-gray-200">
                            <h3 className="text-lg font-semibold text-gray-900">Free</h3>
                            <div className="my-4 flex items-baseline">
                                <span className="text-4xl font-bold text-gray-900">$0</span>
                                <span className="text-gray-500 ml-2">/mo</span>
                            </div>
                            <p className="text-sm text-gray-500 mb-6">Perfect for early-stage startups.</p>
                            <ul className="space-y-3 mb-8 text-sm text-gray-600">
                                <li className="flex">✓ 10 Decisions / mo</li>
                                <li className="flex">✓ 1 User</li>
                                <li className="flex">✓ Manual Entry</li>
                            </ul>
                            <Link href="/register" className="block w-full py-3 px-4 bg-gray-50 text-indigo-600 font-bold text-center rounded-lg hover:bg-gray-100 transition">
                                Get Started
                            </Link>
                        </div>

                        {/* Growth */}
                        <div className="p-8 rounded-2xl border-2 border-indigo-600 relative shadow-2xl">
                            <div className="absolute top-0 right-0 bg-indigo-600 text-white text-xs font-bold px-3 py-1 rounded-bl-lg rounded-tr-lg">POPULAR</div>
                            <h3 className="text-lg font-semibold text-gray-900">Growth</h3>
                            <div className="my-4 flex items-baseline">
                                <span className="text-4xl font-bold text-gray-900">$499</span>
                                <span className="text-gray-500 ml-2">/mo</span>
                            </div>
                            <p className="text-sm text-gray-500 mb-6">For scaling revenue teams.</p>
                            <ul className="space-y-3 mb-8 text-sm text-gray-600">
                                <li className="flex">✓ 500 Decisions / mo</li>
                                <li className="flex">✓ 15 Users</li>
                                <li className="flex">✓ HubSpot & Salesforce</li>
                                <li className="flex">✓ AI Insights</li>
                            </ul>
                            <Link href="/register?plan=growth" className="block w-full py-3 px-4 bg-indigo-600 text-white font-bold text-center rounded-lg hover:bg-indigo-700 transition">
                                Start 14-Day Free Trial
                            </Link>
                        </div>

                        {/* Enterprise */}
                        <div className="p-8 rounded-2xl border border-gray-200">
                            <h3 className="text-lg font-semibold text-gray-900">Enterprise</h3>
                            <div className="my-4 flex items-baseline">
                                <span className="text-4xl font-bold text-gray-900">$4,999</span>
                                <span className="text-gray-500 ml-2">/mo</span>
                            </div>
                            <p className="text-sm text-gray-500 mb-6">For large organizations.</p>
                            <ul className="space-y-3 mb-8 text-sm text-gray-600">
                                <li className="flex">✓ Unlimited Decisions</li>
                                <li className="flex">✓ Unlimited Users</li>
                                <li className="flex">✓ SSO / SAML</li>
                                <li className="flex">✓ Custom Integrations</li>
                            </ul>
                            <Link href="/contact" className="block w-full py-3 px-4 bg-white border border-gray-200 text-gray-900 font-bold text-center rounded-lg hover:bg-gray-50 transition">
                                Contact Sales
                            </Link>
                        </div>
                    </div>
                </div>
            </section>

            {/* Footer */}
            <footer className="bg-gray-900 text-gray-400 py-12">
                <div className="max-w-7xl mx-auto px-6 grid md:grid-cols-4 gap-8">
                    <div className="col-span-1">
                        <div className="text-white font-bold text-xl mb-4">SparqAI</div>
                        <p className="text-sm">
                            The ROI decision intelligence platform for modern revenue teams.
                        </p>
                    </div>
                    <div>
                        <h4 className="text-white font-bold mb-4">Product</h4>
                        <ul className="space-y-2 text-sm">
                            <li><Link href="#features" className="hover:text-white">Features</Link></li>
                            <li><Link href="/pricing" className="hover:text-white">Pricing</Link></li>
                            <li><Link href="/integrations" className="hover:text-white">Integrations</Link></li>
                        </ul>
                    </div>
                    <div>
                        <h4 className="text-white font-bold mb-4">Company</h4>
                        <ul className="space-y-2 text-sm">
                            <li><Link href="/about" className="hover:text-white">About</Link></li>
                            <li><Link href="/blog" className="hover:text-white">Blog</Link></li>
                            <li><Link href="/careers" className="hover:text-white">Careers</Link></li>
                        </ul>
                    </div>
                    <div>
                        <h4 className="text-white font-bold mb-4">Legal</h4>
                        <ul className="space-y-2 text-sm">
                            <li><Link href="/privacy" className="hover:text-white">Privacy</Link></li>
                            <li><Link href="/terms" className="hover:text-white">Terms</Link></li>
                        </ul>
                    </div>
                </div>
                <div className="max-w-7xl mx-auto px-6 mt-12 pt-8 border-t border-gray-800 text-sm text-center">
                    © 2026 SparqAI Inc. All rights reserved.
                </div>
            </footer>
        </div>
    );
}
