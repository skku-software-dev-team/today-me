export interface MusicPick {
  title: string;
  artist: string;
  youtube_url: string;
}

export interface PlacePick {
  name: string;
  address: string;
  maps_url: string;
  reason: string;
}

export interface FoodPick {
  name: string;
  cuisine: string;
  address: string;
  reason: string;
}

export interface StylePick {
  description: string;
  reason: string;
  image_url: string;
  product_url: string;
}

export interface CurateResponse {
  report_id: string;
  music_picks: MusicPick[];
  place_picks: PlacePick[];
  food_picks: FoodPick[];
  style_picks: StylePick[];
  moodboard_url: string | null;
  created_at: string;
}

export interface HistoryReport {
  report_id: string;
  mood: string;
  weather: string;
  energy: number;
  moodboard_url: string | null;
  created_at: string;
}

export interface HistoryResponse {
  total: number;
  reports: HistoryReport[];
}

export type AgentKey = "music" | "place" | "food" | "style";
