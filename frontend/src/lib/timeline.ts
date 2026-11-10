export interface Timeline {
  hour: number
  playing: boolean
  last: number
}

export type TimelineAction =
  | { type: 'seek'; hour: number }
  | { type: 'play' }
  | { type: 'pause' }
  | { type: 'tick' }
  | { type: 'reset'; last: number }

export function timeline(state: Timeline, action: TimelineAction): Timeline {
  switch (action.type) {
    case 'seek':
      return { ...state, hour: Math.max(0, Math.min(state.last, action.hour)) }
    case 'play':
      // Playing from the end starts over.
      return { ...state, playing: true, hour: state.hour >= state.last ? 0 : state.hour }
    case 'pause':
      return { ...state, playing: false }
    case 'tick':
      if (state.hour >= state.last) return { ...state, playing: false }
      return { ...state, hour: state.hour + 1 }
    case 'reset':
      return { hour: 0, playing: false, last: action.last }
  }
}
