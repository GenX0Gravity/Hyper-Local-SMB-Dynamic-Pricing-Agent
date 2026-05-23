import * as React from "react"

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "destructive" | "outline" | "secondary" | "ghost" | "link" | "glow"
  size?: "default" | "sm" | "lg" | "icon"
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className = "", variant = "default", size = "default", ...props }, ref) => {
    const baseStyles = "inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none cursor-pointer"
    
    const variants = {
      default: "bg-slate-900 text-white hover:bg-slate-800 dark:bg-emerald-600 dark:text-white dark:hover:bg-emerald-700 shadow-sm",
      destructive: "bg-red-600 text-white hover:bg-red-700 shadow-sm",
      outline: "border border-slate-700 bg-transparent text-slate-300 hover:bg-slate-800 hover:text-white",
      secondary: "bg-slate-800 text-slate-100 hover:bg-slate-700 shadow-sm",
      ghost: "text-slate-400 hover:bg-slate-800 hover:text-white",
      link: "text-emerald-500 underline-offset-4 hover:underline",
      glow: "bg-emerald-500 text-slate-950 font-semibold shadow-[0_0_15px_rgba(16,185,129,0.3)] hover:shadow-[0_0_25px_rgba(16,185,129,0.6)] hover:bg-emerald-400 transition-all duration-300"
    }

    const sizes = {
      default: "h-10 px-4 py-2",
      sm: "h-9 px-3 rounded-md text-xs",
      lg: "h-11 px-8 rounded-md text-base",
      icon: "h-10 w-10"
    }

    return (
      <button
        className={`${baseStyles} ${variants[variant]} ${sizes[size]} ${className}`}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"
