from collections.abc import Collection, Set

type DropTags = Set
type DragTags = Collection
DEFAULT_DROP_TAGS: DropTags = frozenset((None, ))
DEFAULT_DRAG_TAGS: DragTags = DEFAULT_DROP_TAGS
