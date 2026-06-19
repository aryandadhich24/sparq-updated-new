export type ActionType = 'KILL' | 'SCALE' | 'MAINTAIN' | 'INVESTIGATE';
export type ConfidenceTier = 'DIRECT' | 'HIGH' | 'MODERATE' | 'LOW';

export interface Decision {
    id: number;
    description: string;
    type: 'HIRE' | 'AD_CAMPAIGN' | 'TOOL' | 'VENDOR';
    decision_type?: string;
    start_date?: string;
    cost: number;
    total_cost: number;
    status: string;
    source?: string;
    roi: number;
    value: number;
    confidence: number;
    confidence_tier?: ConfidenceTier;
    action: ActionType;
    details: string;
}

export interface Outcome {
    id: number;
    decision_id?: number;
    metric_name: string;
    value: number;
    date: string;
    description?: string;
    source?: string;
    source_id?: string;
    organization_id?: number;
}

export type DecisionDetail = Decision & {
    start_date: string;
    end_date: string | null;
    explanation: string;
    related_outcomes: {
        id: number;
        date: string;
        description: string | null;
        value: number;
        weight: number;
        share: number;
        attributed_amount: number;
        signal_type?: ConfidenceTier;
    }[];
};
