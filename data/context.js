/* Optional pre-match context layer.
   Keep multipliers near 1.00. Only add an adjustment when you have a sourced reason
   (confirmed lineup, major injury/suspension, or other pre-match information).
   Example:
   "Arsenal__Coventry": {
     "homeAttackMultiplier": 0.97,
     "homeDefenseMultiplier": 1.00,
     "awayAttackMultiplier": 1.00,
     "awayDefenseMultiplier": 1.00,
     "note": "Example only - remove before use",
     "updated": "2026-08-21T17:30:00Z"
   }
*/
window.PREDICTION_CONTEXT = {
  meta: { version: "1.0", policy: "Only sourced, pre-match context. No hindsight edits." },
  fixtures: {}
};
