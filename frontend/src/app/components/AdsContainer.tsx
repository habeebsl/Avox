import React, { ReactNode } from "react";

interface AdsContainerProps {
    children?: ReactNode;
}

export function AdsContainer({ children }: AdsContainerProps) {
    return (
        <div className="flex flex-col gap-1 absolute bottom-30 -right-5">
            {children}
        </div>
    );
}