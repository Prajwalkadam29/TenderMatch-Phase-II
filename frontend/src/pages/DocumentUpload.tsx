import { useState, useRef } from 'react';
import { Upload, FileText, CheckCircle, AlertCircle, Loader2, X, Tag } from 'lucide-react';
import { uploadVendor, uploadTender } from '../services/documentService';
import type { UploadedDocument } from '../types/document';

type DocType = 'vendor' | 'tender';
type UploadStatus = 'idle' | 'uploading' | 'success' | 'error';

interface UploadSlot {
    file: File | null;
    status: UploadStatus;
    result: UploadedDocument | null;
    error: string;
}

const blank = (): UploadSlot => ({ file: null, status: 'idle', result: null, error: '' });

export const DocumentUpload = () => {
    const [vendor, setVendor] = useState<UploadSlot>(blank());
    const [tender, setTender] = useState<UploadSlot>(blank());
    const vendorRef = useRef<HTMLInputElement>(null);
    const tenderRef = useRef<HTMLInputElement>(null);

    const pick = (type: DocType, e: React.ChangeEvent<HTMLInputElement>) => {
        const f = e.target.files?.[0];
        if (!f) return;
        if (type === 'vendor') setVendor(s => ({ ...s, file: f, status: 'idle', error: '', result: null }));
        else setTender(s => ({ ...s, file: f, status: 'idle', error: '', result: null }));
    };

    const run = async (type: DocType) => {
        const slot = type === 'vendor' ? vendor : tender;
        const set  = type === 'vendor' ? setVendor : setTender;
        if (!slot.file) return;
        set(s => ({ ...s, status: 'uploading', error: '' }));
        try {
            const res = type === 'vendor'
                ? await uploadVendor(slot.file)
                : await uploadTender(slot.file);
            set(s => ({ ...s, status: 'success', result: res }));
        } catch (err: unknown) {
            const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Upload failed';
            set(s => ({ ...s, status: 'error', error: typeof msg === 'string' ? msg : JSON.stringify(msg) }));
        }
    };

    const reset = (type: DocType) => {
        if (type === 'vendor') { setVendor(blank()); if (vendorRef.current) vendorRef.current.value = ''; }
        else { setTender(blank()); if (tenderRef.current) tenderRef.current.value = ''; }
    };

    return (
        <div style={{ fontFamily: 'DM Sans' }}>
            {/* Header */}
            <div className="mb-10">
                <span className="pm-badge mb-3">AI-Powered Document Intelligence</span>
                <h1 className="text-4xl font-bold text-[#162f3e] mt-3 mb-2" style={{ fontFamily: 'Poppins' }}>
                    Document <span className="text-[#c41230]">Upload</span>
                </h1>
                <p className="text-[#475569] text-base">
                    Upload vendor or tender PDFs. Groq LLM extracts structured data and generates semantic embeddings automatically.
                </p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <UploadCard
                    type="vendor"
                    label="Vendor Profile"
                    description="Company capabilities, certifications, past projects"
                    slot={vendor}
                    inputRef={vendorRef}
                    onPick={e => pick('vendor', e)}
                    onUpload={() => run('vendor')}
                    onReset={() => reset('vendor')}
                    accentColor="#162f3e"
                />
                <UploadCard
                    type="tender"
                    label="Tender Document"
                    description="Scope of work, eligibility criteria, requirements"
                    slot={tender}
                    inputRef={tenderRef}
                    onPick={e => pick('tender', e)}
                    onUpload={() => run('tender')}
                    onReset={() => reset('tender')}
                    accentColor="#c41230"
                />
            </div>

            {/* Combined result banner */}
            {vendor.result && tender.result && (
                <div className="mt-8 pm-card border-l-4 border-l-green-500 bg-green-50">
                    <div className="flex items-center gap-3 mb-2">
                        <CheckCircle className="w-5 h-5 text-green-600" />
                        <p className="font-semibold text-green-800" style={{ fontFamily: 'Poppins' }}>
                            Both documents indexed! Ready to match.
                        </p>
                    </div>
                    <p className="text-sm text-green-700">
                        Go to <strong>AI Matching</strong> in the sidebar and enter vendor ID{' '}
                        <code className="bg-green-100 px-2 py-0.5 rounded text-xs font-mono">{vendor.result.id}</code>
                        {' '}to see ranked tender matches.
                    </p>
                </div>
            )}
        </div>
    );
};


// ─── UploadCard ───────────────────────────────────────────────────────────────

interface UploadCardProps {
    type: DocType;
    label: string;
    description: string;
    slot: UploadSlot;
    inputRef: React.RefObject<HTMLInputElement | null>;
    onPick: (e: React.ChangeEvent<HTMLInputElement>) => void;
    onUpload: () => void;
    onReset: () => void;
    accentColor: string;
}

const UploadCard = ({ label, description, slot, inputRef, onPick, onUpload, onReset, accentColor }: UploadCardProps) => {
    const { file, status, result, error } = slot;
    const uploading = status === 'uploading';
    const done      = status === 'success';

    return (
        <div className="pm-card flex flex-col gap-5">
            {/* Card header */}
            <div className="flex items-start justify-between">
                <div>
                    <div className="flex items-center gap-2 mb-1">
                        <div className="pm-icon-box" style={{ background: `${accentColor}14`, color: accentColor }}>
                            <FileText className="w-5 h-5" />
                        </div>
                        <h2 className="text-lg font-bold text-[#162f3e]" style={{ fontFamily: 'Poppins' }}>{label}</h2>
                    </div>
                    <p className="text-sm text-[#475569]">{description}</p>
                </div>
                {done && (
                    <span className="text-xs px-2 py-1 rounded-full bg-green-100 text-green-700 font-medium flex items-center gap-1">
                        <CheckCircle className="w-3 h-3" /> Indexed
                    </span>
                )}
            </div>

            {/* Drop zone */}
            {!done ? (
                <div
                    onClick={() => inputRef.current?.click()}
                    className={`
                        border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all duration-200
                        ${file ? 'border-slate-400 bg-slate-50' : 'border-slate-200 hover:border-slate-400 hover:bg-slate-50'}
                    `}
                >
                    <input
                        ref={inputRef}
                        type="file"
                        accept=".pdf,.txt"
                        className="hidden"
                        onChange={onPick}
                    />
                    {file ? (
                        <div className="flex items-center justify-center gap-2 text-[#162f3e]">
                            <FileText className="w-5 h-5 text-[#c41230]" />
                            <span className="text-sm font-medium truncate max-w-[200px]">{file.name}</span>
                            <button
                                onClick={e => { e.stopPropagation(); onReset(); }}
                                className="text-slate-400 hover:text-[#c41230] ml-1"
                            >
                                <X className="w-4 h-4" />
                            </button>
                        </div>
                    ) : (
                        <div>
                            <Upload className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                            <p className="text-sm text-[#475569]">Click to select a <strong>PDF</strong> or <strong>TXT</strong> file</p>
                            <p className="text-xs text-slate-400 mt-1">Max 20 MB</p>
                        </div>
                    )}
                </div>
            ) : (
                <div className="rounded-xl bg-green-50 border border-green-200 p-4">
                    <p className="text-sm text-green-700 font-medium mb-1 flex items-center gap-2">
                        <CheckCircle className="w-4 h-4" /> {result?.original_filename}
                    </p>
                    <p className="text-xs text-slate-500">
                        ID: <span className="font-mono">{result?.id}</span> · FAISS: {result?.embedding_id ?? 'N/A'}
                    </p>
                </div>
            )}

            {/* Error */}
            {status === 'error' && (
                <div className="flex items-start gap-2 p-3 rounded-xl bg-red-50 border border-red-200">
                    <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
                    <p className="text-sm text-red-600">{error}</p>
                </div>
            )}

            {/* Upload button */}
            {!done && (
                <button
                    onClick={onUpload}
                    disabled={!file || uploading}
                    className="pm-btn-primary w-full disabled:opacity-50 disabled:cursor-not-allowed"
                    style={{ background: accentColor, boxShadow: `0 4px 15px ${accentColor}40` }}
                >
                    {uploading ? (
                        <><Loader2 className="w-4 h-4 animate-spin" /> Processing with Groq AI…</>
                    ) : (
                        <><Upload className="w-4 h-4" /> Upload & Extract</>
                    )}
                </button>
            )}

            {done && (
                <button onClick={onReset} className="pm-btn-secondary w-full text-sm">
                    Upload Another
                </button>
            )}

            {/* Extracted results */}
            {done && result && (
                <div className="space-y-4 pt-2 border-t border-slate-100">
                    <ExtractedField label="Scope" value={result.structured_data.scope} />
                    <ExtractedField label="Location" value={result.structured_data.location} />
                    {result.structured_data.certifications.length > 0 && (
                        <div>
                            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Certifications</p>
                            <div className="flex flex-wrap gap-1.5">
                                {result.structured_data.certifications.map(c => (
                                    <span key={c} className="pm-badge text-xs">{c}</span>
                                ))}
                            </div>
                        </div>
                    )}
                    {result.keywords.length > 0 && (
                        <div>
                            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2 flex items-center gap-1">
                                <Tag className="w-3 h-3" /> Keywords
                            </p>
                            <div className="flex flex-wrap gap-1.5">
                                {result.keywords.slice(0, 8).map(k => (
                                    <span key={k} className="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">{k}</span>
                                ))}
                                {result.keywords.length > 8 && (
                                    <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-400">+{result.keywords.length - 8} more</span>
                                )}
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

const ExtractedField = ({ label, value }: { label: string; value?: string }) => {
    if (!value) return null;
    return (
        <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">{label}</p>
            <p className="text-sm text-[#162f3e] leading-relaxed line-clamp-3">{value}</p>
        </div>
    );
};
