import type { ActionItem } from '../types/task'

interface Props {
  items: ActionItem[]
}

export default function ActionItemList({ items }: Props) {
  if (!items || items.length === 0) return null

  return (
    <div className="bg-white rounded-xl shadow p-4">
      <p className="text-xs text-gray-400 uppercase tracking-wide font-medium mb-2">Action Items</p>
      <ul className="space-y-1">
        {items.map((item, i) => (
          <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
            {item.type === 'bullet' ? (
              <span className="mt-1 w-1.5 h-1.5 rounded-full bg-gray-400 flex-shrink-0" />
            ) : item.type === 'ordered' ? (
              <span className="flex-shrink-0 font-medium text-gray-500 w-4">{i + 1}.</span>
            ) : (
              <span className="flex-shrink-0 w-4" />
            )}
            <span>{item.text}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
