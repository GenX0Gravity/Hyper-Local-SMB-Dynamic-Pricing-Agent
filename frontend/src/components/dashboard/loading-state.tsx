export function LoadingState({ message = "Loading..." }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-slate-400">
      <div className="h-10 w-10 animate-spin rounded-full border-2 border-emerald-500 border-t-transparent" />
      <p className="mt-4 text-xs font-semibold tracking-wider">{message}</p>
    </div>
  )
}
