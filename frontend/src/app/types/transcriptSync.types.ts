export interface Sentence {
  text: string;
  start: number;
  end: number;
  insights?: any[];
}

export type Insight = {
    insight: string,
    explanation: string
}