/* Floating background dots matching Parallel Minds homepage */
export const FloatingDots = () => {
    const dots = [
        { top: '8%', left: '6%', size: 6, color: 'rgba(196,18,48,0.5)' },
        { top: '14%', left: '28%', size: 4, color: 'rgba(196,18,48,0.3)' },
        { top: '10%', left: '55%', size: 5, color: 'rgba(100,116,139,0.35)' },
        { top: '20%', left: '72%', size: 4, color: 'rgba(196,18,48,0.25)' },
        { top: '6%', left: '88%', size: 7, color: 'rgba(100,116,139,0.3)' },
        { top: '36%', left: '3%', size: 5, color: 'rgba(196,18,48,0.4)' },
        { top: '45%', left: '92%', size: 9, color: 'rgba(196,18,48,0.6)' },
        { top: '55%', left: '15%', size: 4, color: 'rgba(100,116,139,0.3)' },
        { top: '60%', left: '48%', size: 5, color: 'rgba(196,18,48,0.2)' },
        { top: '70%', left: '80%', size: 4, color: 'rgba(100,116,139,0.3)' },
        { top: '78%', left: '5%', size: 6, color: 'rgba(196,18,48,0.35)' },
        { top: '85%', left: '35%', size: 4, color: 'rgba(100,116,139,0.25)' },
        { top: '92%', left: '65%', size: 5, color: 'rgba(196,18,48,0.3)' },
    ];

    return (
        <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
            {dots.map((dot, i) => (
                <span
                    key={i}
                    className="absolute rounded-full"
                    style={{
                        top: dot.top,
                        left: dot.left,
                        width: dot.size,
                        height: dot.size,
                        backgroundColor: dot.color,
                    }}
                />
            ))}
        </div>
    );
};
