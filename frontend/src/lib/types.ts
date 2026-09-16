export interface Witness {
  first_step: number;
  second_step: number;
  row: number[];
}

export type VerifyOutcome = "collision" | "not_home" | null;

export interface VerifyResponse {
  status: "pass" | "fail";
  outcome: VerifyOutcome;
  bells: number;
  block_size: number;
  repeats: number;
  total_steps: number;
  block_order: number;
  witness: Witness | null;
  final_row: number[] | null;
}

export interface ApiError {
  message: string;
  field: string;
}

export interface VerifyRequest {
  bells: number;
  repeats: number;
  block: number[][];
}
