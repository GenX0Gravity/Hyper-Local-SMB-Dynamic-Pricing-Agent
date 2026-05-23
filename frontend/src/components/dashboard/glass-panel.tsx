import * as React from "react"

interface GlassPanelProps extends React.HTMLAttributes<HTMLDivElement> {
  title?: string
  description?: string
  action?: React.ReactNode
  noPadding?: boolean
}

export function GlassPanel({
  title,
  description,
  action,
  children,
  className = "",
  noPadding = false,
  ...props
}: GlassPanelProps) {
  return (
    <div
      className={`glass-card overflow-hidden rounded-2xl ${className}`}
      {...props}
    >
      {(title || action) && (
        <div className="flex flex-col gap-2 border-b border-white/5 px-5 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <div>
            {title && (
              <h3 className="text-sm font-bold text-white sm:text-base">{title}</h3>
            )}
            {description && (
              <p className="mt-0.5 text-xs text-slate-500">{description}</p>
            )}
          </div>
          {action}
        </div>
      )}
      <div className={noPadding ? "" : "p-5 sm:p-6"}>{children}</div>
    </div>
  )
}
