import { ReactNode } from "react";

export function Card({ children, className }: { children: ReactNode; className?: string }) {
    return <div className={`bg-white border border-gray-200 ${className}`}>{children}</div>;
}

export function CardContent({ children }: { children: ReactNode }) {
    return <div className="p-4">{children}</div>;
}
