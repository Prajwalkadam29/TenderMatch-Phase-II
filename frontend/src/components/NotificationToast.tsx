import React, { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Sparkles, X, Target, BellRing } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { matchingService } from '../services/matchingService';

export const NotificationToast = () => {
    const [lastSeenId, setLastSeenId] = useState<string | null>(null);
    const [activeToast, setActiveToast] = useState<{ id: string, title: string, score: number, time: number } | null>(null);

    const { data: history = [] } = useQuery({
        queryKey: ['matchHistoryLatest'],
        queryFn: () => matchingService.getHistory({ limit: 5 }),
        refetchInterval: 30000, // Poll every 30 seconds
    });

    useEffect(() => {
        if (!history.length) return;

        // Find the newest match that is a high score
        const newestMatch = history[0];
        
        // Initialize lastSeenId on first load so we don't spam old matches
        if (!lastSeenId) {
            setLastSeenId(newestMatch.match_id);
            return;
        }

        // If it's a new match and score > 75, show it
        if (newestMatch.match_id !== lastSeenId && newestMatch.final_score > 75) {
            setLastSeenId(newestMatch.match_id);
            setActiveToast({
                id: newestMatch.match_id,
                title: newestMatch.tender_id, // We use tender_id as title since we don't have full title in history item
                score: newestMatch.final_score,
                time: Date.now()
            });

            // Auto dismiss after 8 seconds
            setTimeout(() => {
                setActiveToast(prev => prev?.id === newestMatch.match_id ? null : prev);
            }, 8000);
        }
    }, [history, lastSeenId]);

    return (
        <AnimatePresence>
            {activeToast && (
                <motion.div
                    initial={{ opacity: 0, y: 50, scale: 0.9 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.9, y: 20 }}
                    className="fixed bottom-6 right-6 z-50 pm-card p-4 pr-10 shadow-2xl border-l-4 border-l-emerald-500 bg-white max-w-sm"
                >
                    <button 
                        onClick={() => setActiveToast(null)}
                        className="absolute top-3 right-3 text-slate-400 hover:text-slate-600 transition"
                    >
                        <X className="w-4 h-4" />
                    </button>
                    <div className="flex gap-3 items-start">
                        <div className="w-10 h-10 rounded-full bg-emerald-100 flex items-center justify-center flex-shrink-0">
                            <Sparkles className="w-5 h-5 text-emerald-600" />
                        </div>
                        <div>
                            <p className="text-[10px] font-black text-emerald-600 uppercase tracking-widest mb-1 flex items-center gap-1">
                                <BellRing className="w-3 h-3" /> Auto-Match Alert
                            </p>
                            <p className="text-sm font-bold text-[#162f3e] leading-tight mb-1" style={{ fontFamily: 'Poppins' }}>
                                New high-confidence match found!
                            </p>
                            <div className="flex items-center gap-2 mt-2">
                                <span className="inline-flex items-center gap-1 text-[10px] font-bold text-slate-500 bg-slate-50 px-2 py-1 rounded-md border border-slate-200 truncate max-w-[150px]">
                                    <Target className="w-3 h-3" /> {activeToast.title}
                                </span>
                                <span className="text-xs font-black text-emerald-600">
                                    {Math.round(activeToast.score)}% Score
                                </span>
                            </div>
                        </div>
                    </div>
                </motion.div>
            )}
        </AnimatePresence>
    );
};
