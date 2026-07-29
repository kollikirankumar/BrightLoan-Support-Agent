export default function BrandMark({ size = 'md' }) {
  const dimensions = size === 'sm' ? 'h-8 w-8 text-sm' : 'h-11 w-11 text-lg'
  return (
    <div
      className={`flex ${dimensions} shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 via-violet-500 to-sky-500 font-bold text-white shadow-md shadow-indigo-200`}
    >
      B
    </div>
  )
}
