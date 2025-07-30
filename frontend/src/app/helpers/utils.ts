import { Sentence } from "../types/transcriptSync.types";

export const mapInsightsToSentences = (sentences: Sentence[], insights: any[]) => {
  return sentences.map((sentence, sentenceIndex) => {
    const mappedInsights = insights
      .map(insight => {
        const startChar = sentence.text.indexOf(insight.insight);
        if (startChar === -1) return null;
        
        return {
          insight: insight.insight,
          explanation: insight.explanation,
          sentenceIndex,
          startChar,
          endChar: startChar + insight.insight.length
        };
      })
      .filter(Boolean); 
    
    return {
      ...sentence,
      insights: mappedInsights
    };
  });
};

export function isJsonString(data: any): boolean {
  try {
    JSON.parse(data);
    return true;
  } catch {
    return false;
  }
}

export function getRandomVibrantColor(): string {
  const vibrantColors = [
    '#FF5733', // orange-red
    '#FF6F61', // coral
    '#FFC300', // vibrant yellow
    '#FF33A8', // hot pink
    '#00C1D4', // aqua blue
    '#28B463', // emerald green
    '#9B59B6', // amethyst
    '#E74C3C', // red
    '#3498DB', // sky blue
    '#F39C12', // orange
    '#1ABC9C', // teal
    '#8E44AD', // deep purple
  ];

  const index = Math.floor(Math.random() * vibrantColors.length);
  return vibrantColors[index];
}