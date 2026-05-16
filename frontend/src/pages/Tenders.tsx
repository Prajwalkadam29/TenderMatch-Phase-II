import React, { useState, useEffect, useMemo } from 'react';
import type { Tender } from '../types/tender';
import { TenderCard } from '../components/TenderCard';
import { 
    Filter, Download, Database, Users, 
    BrainCircuit, Search, Loader2, Info,
    AlertCircle, Sparkles
} from 'lucide-react';
import { vendorProfileService } from '../services/vendorProfileApi';
import { getAllTenders, matchVendor } from '../services/documentService';
import type { VendorProfileResponse } from '../types/vendorProfile';
import type { MatchResult, UploadedDocument } from '../types/document';

export const Tenders: React.FC = () => {
    const [profiles, setProfiles] = useState<VendorProfileResponse[]>([]);
    const [selectedProfileId, setSelectedProfileId] = useState<string>('all');
    const [tenders, setTenders] = useState<Tender[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');
    const [selectedCategory, setSelectedCategory] = useState('All Tenders');

    const categories = [
        'All Tenders',
        'Civil & Construction',
        'Electrical & Instrumentation',
        'IT & Software',
        'Healthcare',
        'Renewable Energy',
        'Supply / Procurement',
    ];

    useEffect(() => {
        const init = async () => {
            try {
                const profileData = await vendorProfileService.list();
                setProfiles(profileData);
                // If there's at least one profile, maybe default to it? 
                // For now, let's default to "All" to show everything.
            } catch (err) {
                console.error('Failed to load profiles', err);
            }
        };
        init();
    }, []);

    useEffect(() => {
        const fetchTenders = async () => {
            setLoading(true);
            try {
                if (selectedProfileId === 'all') {
                    const rawDocs = await getAllTenders();
                    const mapped: Tender[] = rawDocs.map(doc => ({
                        id: doc.id,
                        title: doc.original_filename.split('_').slice(1).join('_') || doc.original_filename,
                        organization: (doc.structured_data as any)?.organization || 'System Scraped',
                        deadline: (doc.structured_data as any)?.deadline || new Date().toISOString(),
                        matchScore: 0, // No score in "All" mode
                        status: 'Open',
                        scope: doc.structured_data.scope,
                    }));
                    setTenders(mapped);
                } else {
                    // We need a document ID for matching, but here we have a vendor_profile ID.
                    // Wait, the match API expects a "vendor document ID" (the one from /upload/vendor).
                    // Does the user have a vendor document?
                    // Let's check if the profile has a linked document_id or if we can use profile directly.
                    // Actually, the current backend /match/{vendor_id} expects a document ID.
                    
                    // Let's look for a document of type 'vendor' for this user.
                    // Optimization: For this Phase, if we don't have a document, we show a message.
                    const { getMyDocuments } = await import('../services/documentService');
                    const myDocs = await getMyDocuments('vendor');
                    
                    if (myDocs.length > 0) {
                        // Use the first vendor doc for matching
                        const matchData = await matchVendor(myDocs[0].id);
                        const mapped: Tender[] = matchData.results.map(m => ({
                            id: m.tender_id,
                            title: m.tender_filename,
                            organization: (m.match_result as any)?.tender_summary?.organization || 'Tender Entity',
                            deadline: (m.match_result as any)?.tender_summary?.deadline || new Date().toISOString(),
                            matchScore: Math.round(m.final_score),
                            status: 'Open',
                            scope: m.tender_summary.scope,
                        }));
                        setTenders(mapped);
                    } else {
                        setTenders([]);
                    }
                }
            } catch (err) {
                console.error('Failed to fetch tenders', err);
            } finally {
                setLoading(false);
            }
        };

        fetchTenders();
    }, [selectedProfileId]);

    const filteredTenders = useMemo(() => {
        return tenders.filter(t => {
            const matchesSearch = t.title.toLowerCase().includes(searchTerm.toLowerCase()) || 
                                 t.organization.toLowerCase().includes(searchTerm.toLowerCase());
            const matchesCat = selectedCategory === 'All Tenders' || t.title.includes(selectedCategory) || (t.scope && t.scope.includes(selectedCategory));
            return matchesSearch && matchesCat;
        });
    }, [tenders, searchTerm, selectedCategory]);

    return (
        <div style={{ fontFamily: 'DM Sans' }}>
            {/* Page header */}
            <div className="mb-10 flex flex-col md:flex-row md:items-end justify-between gap-6">
                <div>
                    <span className="pm-badge mb-3">AI Discovery Engine v2.1</span>
                    <h1 className="text-4xl font-bold text-[#162f3e] mt-3 mb-2" style={{ fontFamily: 'Poppins' }}>
                        Tender <span className="text-[#c41230]">Intelligence</span>
                    </h1>
                    <p className="text-[#475569] text-base">
                        {selectedProfileId === 'all' 
                            ? "Exploring all active tenders in the system database." 
                            : "AI-ranked tenders dynamically matched to your business profile."}
                    </p>
                </div>

                <div className="flex flex-col sm:row items-start sm:items-center gap-3">
                    <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest ml-1 mb-1 sm:mb-0">Select Matching Persona</div>
                    <div className="relative">
                        <Users className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                        <select 
                            value={selectedProfileId}
                            onChange={(e) => setSelectedProfileId(e.target.value)}
                            className="pl-10 pr-10 py-2.5 bg-white border border-slate-200 rounded-xl text-sm font-medium text-[#162f3e] focus:outline-none focus:border-[#c41230] appearance-none cursor-pointer min-w-[200px]"
                        >
                            <option value="all">Global (No Matching)</option>
                            {profiles.map(p => (
                                <option key={p.id} value={p.id}>{p.identity.company_legal_name}</option>
                            ))}
                        </select>
                    </div>
                </div>
            </div>

            {/* PM-style two-column: left vertical tabs + right content */}
            <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
                {/* Left column: Vertical nav tiles */}
                <div className="lg:col-span-1 space-y-2">
                    <div className="flex items-center justify-between mb-4 px-1">
                        <div className="flex items-center gap-2">
                            <Database className="w-4 h-4 text-[#c41230]" />
                            <span className="text-xs text-slate-400 font-bold uppercase tracking-wider">Sectors</span>
                        </div>
                    </div>
                    {categories.map((cat) => (
                        <button
                            key={cat}
                            onClick={() => setSelectedCategory(cat)}
                            className={`w-full text-left px-5 py-4 rounded-xl border text-[13px] font-bold transition-all duration-200
                                ${selectedCategory === cat
                                    ? 'bg-[#162f3e] text-white border-[#162f3e] shadow-lg shadow-[#162f3e]/10'
                                    : 'bg-white border-slate-200 text-[#475569] hover:border-slate-300 hover:bg-slate-50 hover:text-[#162f3e]'
                                }`}
                        >
                            {cat}
                        </button>
                    ))}

                    <div className="mt-8 p-5 rounded-2xl bg-slate-50 border border-slate-100">
                        <div className="flex items-center gap-2 mb-3 text-[#162f3e]">
                            <BrainCircuit className="w-4 h-4" />
                            <span className="text-xs font-bold uppercase tracking-widest">Match Logic</span>
                        </div>
                        <p className="text-[11px] text-[#475569] leading-relaxed">
                            Our engine uses <span className="font-bold text-[#c41230]">pgvector</span> for semantic distance and LLM verification for eligibility scoring.
                        </p>
                    </div>
                </div>

                {/* Right column: Tender cards grid */}
                <div className="lg:col-span-3 space-y-6">
                    {/* Toolbar */}
                    <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
                        <div className="relative flex-1 w-full max-w-md">
                            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                            <input 
                                type="text"
                                placeholder="Quick search matches..."
                                value={searchTerm}
                                onChange={(e) => setSearchTerm(e.target.value)}
                                className="w-full pl-11 pr-4 py-3 bg-white border border-slate-200 rounded-2xl text-sm focus:outline-none focus:border-[#c41230] transition-all"
                            />
                        </div>
                        <div className="flex gap-3 w-full sm:w-auto">
                            <button className="flex-1 sm:flex-none pm-btn-secondary text-xs py-3 px-4">
                                <Filter className="w-4 h-4" /> Parameters
                            </button>
                            <button className="flex-1 sm:flex-none pm-btn-primary text-xs py-3 px-6 shadow-lg shadow-[#c41230]/10">
                                <Download className="w-4 h-4" /> Export Results
                            </button>
                        </div>
                    </div>

                    {/* Content Area */}
                    {loading ? (
                        <div className="py-20 flex flex-col items-center justify-center text-slate-400">
                            <Loader2 className="w-10 h-10 animate-spin mb-4 text-[#c41230]" />
                            <p className="text-sm font-medium">Analyzing database patterns...</p>
                        </div>
                    ) : filteredTenders.length === 0 ? (
                        <div className="py-20 px-10 text-center bg-white border border-slate-100 rounded-3xl flex flex-col items-center">
                            <div className="w-16 h-16 bg-slate-50 rounded-full flex items-center justify-center mb-6">
                                <AlertCircle className="w-8 h-8 text-slate-300" />
                            </div>
                            <h3 className="text-xl font-bold text-[#162f3e]" style={{ fontFamily: 'Poppins' }}>No tenders found</h3>
                            <p className="text-[#475569] mt-2 max-w-xs mx-auto text-sm">
                                {selectedProfileId !== 'all' 
                                    ? "We couldn't find any strong matches for this profile. Try uploading a more detailed capability statement." 
                                    : "The system is currently empty. Start by uploading or scraping new tenders."}
                            </p>
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-5">
                            {filteredTenders.map(tender => (
                                <TenderCard key={tender.id} tender={tender} />
                            ))}
                        </div>
                    )}

                    {/* Footer Info */}
                    {!loading && filteredTenders.length > 0 && (
                        <div className="pt-6 border-t border-slate-100 flex items-center gap-3 text-slate-400">
                            <Sparkles className="w-4 h-4 text-amber-400" />
                            <span className="text-[11px] font-medium tracking-tight">
                                {selectedProfileId === 'all' 
                                    ? "Showing generic results. Select a profile for AI-ranked intelligence." 
                                    : `AI has ranked these ${filteredTenders.length} opportunities based on your technical capabilities and past experience.`}
                            </span>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};
