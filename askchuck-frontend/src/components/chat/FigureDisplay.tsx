"use client";

import { Figure } from "@/types/chat";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import Image from "next/image";

interface FigureDisplayProps {
  figures: Figure[];
}

export function FigureDisplay({ figures }: FigureDisplayProps) {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <div className="h-px flex-1 bg-gradient-to-r from-transparent via-border to-transparent" />
        <span className="text-xs uppercase tracking-wider text-muted-foreground font-serif">
          Figures
        </span>
        <div className="h-px flex-1 bg-gradient-to-r from-transparent via-border to-transparent" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {figures.map((figure, index) => (
          <Card
            key={`${figure.document}-${figure.figure_number}`}
            className="group overflow-hidden border-2 border-border hover:border-primary transition-all duration-500 animate-in fade-in slide-in-from-bottom-2"
            style={{ animationDelay: `${index * 150}ms` }}
          >
            {/* Image container with vintage border effect */}
            <div className="relative aspect-[4/3] bg-muted overflow-hidden">
              <div className="absolute inset-0 border-4 border-background/50 pointer-events-none z-10" />
              <Image
                src={figure.url}
                alt={figure.caption || figure.description}
                fill
                className="object-contain p-4 transition-transform duration-700 group-hover:scale-105"
                unoptimized
              />

              {/* Figure number badge - top right corner */}
              <div className="absolute top-3 right-3 z-20">
                <Badge variant="secondary" className="bg-background/90 backdrop-blur-sm text-xs font-mono">
                  Fig. {figure.figure_number}
                </Badge>
              </div>
            </div>

            {/* Caption - elegant typography */}
            <div className="p-4 bg-card border-t border-border">
              <p className="text-sm text-foreground leading-relaxed italic">
                {figure.caption || figure.description}
              </p>
              <p className="text-xs text-muted-foreground mt-2">
                {figure.document}
              </p>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
