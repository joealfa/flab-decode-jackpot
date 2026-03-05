"""
AI Analyzer Module
Uses Ollama (llama3.1:8b) to provide intelligent analysis and predictions
based on lottery statistical data.
"""

import logging
from typing import Dict, List, Optional, Any
import ollama

from app.config import config
from app.exceptions import InternalServerException

logger = logging.getLogger(__name__)


class AIAnalyzer:
    """
    AI-powered lottery analysis using Ollama.

    Provides intelligent interpretation of statistical analysis and
    generates recommendations for likely number combinations.
    """

    def __init__(self, model: Optional[str] = None):
        """
        Initialize AI Analyzer.

        Args:
            model: Ollama model name (defaults to config.OLLAMA_MODEL)
        """
        self.model = model or config.OLLAMA_MODEL
        logger.info(f"AI Analyzer initialized with model: {self.model}")

    def check_ollama_status(self) -> Dict[str, Any]:
        """
        Check if Ollama is running and the model is available.

        Returns:
            Dictionary with status information
        """
        try:
            # Try to list available models
            models_response = ollama.list()

            # Extract model names from response
            available_models = []

            # Handle Pydantic model response (ollama>=0.6.0)
            if hasattr(models_response, "models"):
                for model in models_response.models:
                    if hasattr(model, "model"):
                        available_models.append(model.model)
            # Handle dict response (older versions)
            elif isinstance(models_response, dict):
                models_list = models_response.get("models", [])
                for model in models_list:
                    if isinstance(model, dict):
                        model_name = model.get("model") or model.get("name", "")
                        if model_name:
                            available_models.append(model_name)

            # Check if configured model is available (exact or partial match)
            model_available = any(
                self.model in m or m.startswith(self.model) for m in available_models
            )

            return {
                "running": True,
                "model_available": model_available,
                "available_models": available_models,
                "configured_model": self.model,
            }
        except Exception as e:
            logger.warning(f"Ollama status check failed: {str(e)}")
            return {"running": False, "error": str(e)}

    def analyze_lottery_report(self, analysis_data: Dict) -> Dict[str, Any]:
        """
        Analyze lottery statistical report using AI.

        Args:
            analysis_data: Complete analysis report from LotteryAnalyzer

        Returns:
            Dictionary containing AI analysis, summary, and top 5 predictions

        Raises:
            InternalServerException: If AI analysis fails
        """
        try:
            # Extract key information from analysis
            game_type = analysis_data.get("game_type", "Unknown")
            total_draws = (
                analysis_data.get("total_draws")
                or analysis_data.get("overall_stats", {}).get("total_draws")
                or analysis_data.get("summary", {}).get("total_draws", 0)
            )
            date_range = analysis_data.get("date_range", {})

            # Build comprehensive prompt directly from analysis_data
            prompt = self._build_analysis_prompt_v2(analysis_data)

            logger.info(f"Sending analysis to AI model: {self.model}")
            logger.debug(f"Prompt length: {len(prompt)} characters")

            # Call Ollama API
            response = ollama.chat(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert statistician and data analyst specializing in Philippine PCSO (Philippine Charity Sweepstakes Office) lottery analysis. "
                            "You have deep knowledge of probability theory, statistical analysis, and pattern recognition. "
                            "Your role is to analyze historical lottery draw data and provide intelligent, data-driven insights.\n\n"
                            "IMPORTANT CONTEXT:\n"
                            "- The Philippine PCSO operates multiple lottery games (Ultra Lotto 6/58, Grand Lotto 6/55, Super Lotto 6/49, Mega Lotto 6/45, Lotto 6/42)\n"
                            "- Each game draws a specific number of balls from a fixed range (e.g., 6/58 means pick 6 numbers from 1-58)\n"
                            "- Draws occur 2-3 times per week depending on the game\n"
                            "- All draws are random and independent events\n\n"
                            "YOUR ANALYTICAL APPROACH:\n"
                            "1. Identify statistically significant patterns in the data\n"
                            "2. Consider frequency analysis (hot/cold numbers)\n"
                            "3. Examine distribution patterns (even/odd, high/low, consecutive)\n"
                            "4. Analyze temporal trends (day of week patterns, recent vs historical)\n"
                            "5. Evaluate multiple prediction algorithms\n"
                            "6. Always acknowledge that past results do NOT guarantee future outcomes\n\n"
                            "RESPONSE STYLE:\n"
                            "- Be analytical but accessible to non-technical users\n"
                            "- Use clear explanations without excessive jargon\n"
                            "- Provide actionable insights\n"
                            "- Always include a responsible gaming disclaimer\n"
                            "- Format in markdown for readability"
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                options={
                    "temperature": 0.7,  # Balanced creativity/consistency
                    "top_p": 0.9,
                    "num_predict": 4096,  # Max tokens for comprehensive response
                },
            )

            ai_response = response["message"]["content"]
            logger.info(
                f"AI analysis completed. Response length: {len(ai_response)} characters"
            )

            return {
                "success": True,
                "model": self.model,
                "game_type": game_type,
                "analysis": ai_response,
                "total_draws_analyzed": total_draws,
                "date_range": date_range,
            }

        except Exception as e:
            logger.error(f"AI analysis failed: {str(e)}", exc_info=True)
            raise InternalServerException(
                message="AI analysis failed",
                details={"error": str(e), "model": self.model},
            )

    def _build_analysis_prompt_v2(self, analysis_data: Dict) -> str:
        """
        Build comprehensive analysis prompt from the full analysis data.

        Extracts ALL available data sections from the analysis JSON
        to give the AI the most complete context possible.

        Args:
            analysis_data: Complete analysis report dictionary

        Returns:
            Formatted prompt string
        """
        # === Extract all data sections ===
        game_type = analysis_data.get("game_type", "Unknown")
        date_range = analysis_data.get("date_range", {})
        total_draws = analysis_data.get("total_draws") or analysis_data.get(
            "overall_stats", {}
        ).get("total_draws", 0)
        if total_draws <= 0:
            logger.warning(f"Invalid total_draws: {total_draws}. Using 1.")
            total_draws = 1

        # Parse game parameters
        max_num = int(game_type.split("/")[-1])
        numbers_to_pick = int(game_type.split("/")[0].split()[-1])

        overall_stats = analysis_data.get("overall_stats", {})
        day_analysis = analysis_data.get("day_analysis", {})
        pattern_analysis = analysis_data.get("pattern_analysis", {})
        temporal_patterns = analysis_data.get("temporal_patterns", {})
        historical_observations = analysis_data.get("historical_observations", {})

        # Frequency data
        most_frequent = overall_stats.get("most_frequent_numbers", [])[:15]
        least_frequent = overall_stats.get("least_frequent_numbers", [])[:15]
        hot_numbers = overall_stats.get("hot_numbers", [])
        cold_numbers = overall_stats.get("cold_numbers", [])
        avg_frequency = overall_stats.get("average_frequency", 0)

        # Pattern data
        even_odd = overall_stats.get("even_odd_analysis", {})
        high_low = overall_stats.get("high_low_analysis", {})
        consecutive = overall_stats.get("consecutive_analysis", {})
        sum_analysis = overall_stats.get("sum_analysis", {})

        # Winner analysis
        winner = overall_stats.get("winner_analysis", {})

        # Predictions
        top_preds = analysis_data.get("top_predictions", [])[:5]
        winning_preds = analysis_data.get("winning_predictions", [])[:5]
        pattern_preds = analysis_data.get("pattern_predictions", [])[:5]
        ultimate_preds = analysis_data.get("ultimate_predictions", [])[:5]

        # Draw transition patterns
        latest_draw = pattern_analysis.get("latest_draw", {})

        # Year-over-year trends
        yoy_trends = temporal_patterns.get("year_over_year_trends", {})

        # === Build prompt sections ===
        prompt = f"""# PCSO Lottery Statistical Analysis Request

## 📊 LOTTERY GAME INFORMATION

**Game Type:** {game_type} (Philippine PCSO)
**Analysis Period:** {date_range.get("start", "N/A")} to {date_range.get("end", "N/A")}
**Total Historical Draws:** {total_draws:,} draws
**Number Range:** 1 to {max_num}
**Numbers Per Draw:** {numbers_to_pick} numbers

---

## 📈 COMPREHENSIVE STATISTICAL DATA

### 1️⃣ FREQUENCY ANALYSIS

**"Hot Numbers" (Most Frequent, Top 15):**
{self._format_frequency_list(most_frequent)}

**"Cold Numbers" (Least Frequent, Top 15):**
{self._format_frequency_list(least_frequent)}

**Summary:**
- Hot numbers (top 10): {hot_numbers[:10] if isinstance(hot_numbers, list) else "N/A"}
- Cold numbers (top 10): {cold_numbers[:10] if isinstance(cold_numbers, list) else "N/A"}
- Average frequency per number: {avg_frequency:.1f}
- Expected avg frequency: {((total_draws * numbers_to_pick / max_num) if total_draws > 0 else 0):.1f}
- Actual range: {least_frequent[-1][1] if least_frequent else "N/A"} to {most_frequent[0][1] if most_frequent else "N/A"}

---

### 2️⃣ PATTERN & DISTRIBUTION ANALYSIS

**Even/Odd Distribution:**
{self._format_pattern_dict(even_odd.get("patterns", {}))}
- Most common pattern: {even_odd.get("most_common_pattern", "N/A")}

**High/Low Balance (midpoint: {high_low.get("mid_point", max_num // 2)}):**
{self._format_pattern_dict(high_low.get("patterns", {}))}
- Most common pattern: {high_low.get("most_common_pattern", "N/A")}

**Consecutive Numbers:**
- Average consecutive per draw: {consecutive.get("average_consecutive", 0):.2f}
- Max consecutive seen: {consecutive.get("max_consecutive", 0)}
- Draws with consecutive numbers: {consecutive.get("draws_with_consecutive", 0):,} ({consecutive.get("percentage_with_consecutive", 0):.1f}%)

**Sum Analysis:**
- Average sum: {sum_analysis.get("average_sum", 0):.1f}
- Median sum: {sum_analysis.get("median_sum", 0):.1f}
- Range: {sum_analysis.get("min_sum", 0)} to {sum_analysis.get("max_sum", 0)}
- Std dev: {sum_analysis.get("std_dev", 0):.1f}

---

### 3️⃣ DRAW TRANSITION PATTERNS (Consecutive Draw Analysis)

- Average numbers carried over between draws: {pattern_analysis.get("average_carryover", 0):.2f}
- Most common carryover count: {pattern_analysis.get("most_common_carryover", 0)}
- Average new numbers per draw: {pattern_analysis.get("average_new_numbers", 0):.2f}
- Average sum difference between draws: {pattern_analysis.get("average_sum_difference", 0):.1f}
- Most common even/odd transition: {pattern_analysis.get("most_common_pattern_transition", "N/A")}
{self._format_latest_draw(latest_draw)}

---

### 4️⃣ WINNER ANALYSIS (Jackpot Winners)

{self._format_winner_analysis(winner)}

---

### 5️⃣ DAY-OF-WEEK ANALYSIS

{self._format_day_analysis(day_analysis)}

---

### 6️⃣ TEMPORAL PATTERNS

**Day-of-Week Hot Numbers:**
{self._format_temporal_day_of_week(temporal_patterns.get("by_day_of_week", {}))}

**Year-over-Year Consistent Performers:**
{self._format_consistent_performers(yoy_trends.get("consistent_performers", []))}

**Distinct High Performers by Year:**
{self._format_high_performers(yoy_trends.get("distinct_high_performers", []))}

---

### 7️⃣ HISTORICAL OBSERVATIONS & INSIGHTS

{self._format_historical_observations(historical_observations)}

---

### 8️⃣ ALGORITHMIC PREDICTIONS (4 Different Methods)

**Algorithm 1: Frequency-Based (Weighted by recent performance)**
{self._format_prediction_list_detailed(top_preds)}

**Algorithm 2: Winning Pattern Analysis (Based on actual winner characteristics)**
{self._format_prediction_list_detailed(winning_preds)}

**Algorithm 3: Pattern-Based (Considers distribution patterns)**
{self._format_prediction_list_detailed(pattern_preds)}

**Algorithm 4: Ultimate Multi-Dimensional (Combines all factors)**
{self._format_prediction_list_detailed(ultimate_preds)}

---

## 🎯 YOUR ANALYTICAL TASK

Please provide a comprehensive analysis in the following format:

### 1. EXECUTIVE SUMMARY (3-4 paragraphs)
High-level overview of the most important findings from this {total_draws:,} draw dataset. Key statistical patterns, surprising trends, and what makes this game's distribution unique.

### 2. STATISTICAL INSIGHTS (Detailed Analysis)

**a) Frequency Analysis Interpretation:**
- What do the hot/cold number patterns tell us?
- Are there any statistically significant deviations from expected frequency?

**b) Pattern & Distribution Analysis:**
- Analysis of even/odd and high/low balance
- Significance of consecutive number occurrences
- Sum range patterns and what they indicate

**c) Winner Pattern Analysis:**
- What patterns emerge from draws that had jackpot winners?
- Are certain days or months more favorable?

**d) Temporal Trends:**
- Year-over-year consistency patterns
- Which numbers are consistent performers across many years?
- Any recent shifts in patterns?

### 3. AI-RECOMMENDED TOP 5 NUMBER COMBINATIONS

Based on ALL the statistical data provided above (frequency, patterns, winner analysis, temporal trends, historical observations, and the 4 algorithmic predictions), generate your own 5 best combinations. For each:

🎲 **Combination N:** [numbers]
   - **Reasoning:** Why this combination based on the data
   - **Key factors:** (e.g., hot numbers, balanced distribution, winner patterns)

**Your combinations should:**
- Be {numbers_to_pick} numbers between 1 and {max_num}
- Consider ALL data: frequency, patterns, winner analysis, temporal trends
- Have balanced even/odd and high/low distribution
- Fall within the typical sum range ({sum_analysis.get("average_sum", 0):.0f} ± {sum_analysis.get("std_dev", 0):.0f})
- Be clearly distinct from each other
- Have solid statistical reasoning

### 4. CONFIDENCE ASSESSMENT
Rate each combination 1-5 stars (⭐) based on statistical strength.

### 5. IMPORTANT DISCLAIMER ⚠️
Remind users about the random nature of lottery draws and responsible gaming.

---

**REMEMBER:** Be specific, reference actual numbers from the statistics. Make reasoning transparent and educational. Format in clean markdown.
"""

        return prompt

    def _format_pattern_dict(self, patterns: Dict) -> str:
        """Format a pattern distribution dictionary."""
        if not patterns:
            return "No pattern data available"
        # Sort by count descending
        sorted_patterns = sorted(patterns.items(), key=lambda x: x[1], reverse=True)
        lines = [f"- {pattern}: {count:,} draws" for pattern, count in sorted_patterns]
        return "\n".join(lines)

    def _format_latest_draw(self, latest_draw: Dict) -> str:
        """Format the latest draw information."""
        if not latest_draw:
            return ""
        return (
            f"- Latest draw: {latest_draw.get('date', 'N/A')} → "
            f"{latest_draw.get('numbers', [])} (sum: {latest_draw.get('sum', 'N/A')})"
        )

    def _format_winner_analysis(self, winner: Dict) -> str:
        """Format winner/jackpot analysis data."""
        if not winner:
            return "No winner analysis data available"

        lines = []

        total_wins = winner.get("total_winning_draws", 0)
        win_rate = winner.get("win_rate", 0)
        lines.append(f"**Total Jackpot Wins:** {total_wins} ({win_rate}% of draws)")

        # Hot winning numbers
        hot_winning = winner.get("hot_winning_numbers", [])
        if hot_winning:
            lines.append(f"**Hot Winning Numbers:** {hot_winning[:10]}")

        # Most frequent winning numbers with counts
        freq_winning = winner.get("most_frequent_winning_numbers", [])
        if freq_winning:
            formatted = [f"{num} ({count}x)" for num, count in freq_winning[:10]]
            lines.append(f"**Most Frequent in Winning Draws:** {', '.join(formatted)}")

        # Best winning days
        best_days = winner.get("best_winning_days", [])
        if best_days:
            formatted = [f"{day} ({count})" for day, count in best_days]
            lines.append(f"**Best Winning Days:** {', '.join(formatted)}")

        # Best winning months
        best_months = winner.get("best_winning_months", [])
        if best_months:
            month_names = {
                1: "Jan",
                2: "Feb",
                3: "Mar",
                4: "Apr",
                5: "May",
                6: "Jun",
                7: "Jul",
                8: "Aug",
                9: "Sep",
                10: "Oct",
                11: "Nov",
                12: "Dec",
            }
            formatted = [
                f"{month_names.get(m, m)} ({count})" for m, count in best_months
            ]
            lines.append(f"**Best Winning Months:** {', '.join(formatted)}")

        # Winning even/odd patterns
        w_eo = winner.get("winning_even_odd_patterns", {})
        if w_eo:
            lines.append(
                f"**Winning Even/Odd Pattern:** {w_eo.get('most_common_pattern', 'N/A')} (most common)"
            )

        # Winning high/low patterns
        w_hl = winner.get("winning_high_low_patterns", {})
        if w_hl:
            lines.append(
                f"**Winning High/Low Pattern:** {w_hl.get('most_common_pattern', 'N/A')} (most common)"
            )

        # Jackpot stats
        jackpot = winner.get("jackpot_stats", {})
        if jackpot:
            lines.append(
                f"**Jackpot Stats:** Avg ₱{jackpot.get('average', 0):,.0f} | "
                f"Min ₱{jackpot.get('min', 0):,.0f} | Max ₱{jackpot.get('max', 0):,.0f}"
            )

        # Next win probability
        nwp = winner.get("next_win_probability", {})
        if nwp:
            lines.append(
                f"**Win Frequency:** Avg {nwp.get('average_days_between_wins', 0):.0f} days between wins | "
                f"Last win: {nwp.get('last_win_date', 'N/A')} | "
                f"Days since: {nwp.get('days_since_last_win', 'N/A')}"
            )

        return "\n".join(lines)

    def _format_day_analysis(self, day_analysis: Dict) -> str:
        """Format the day_analysis section."""
        if not day_analysis:
            return "No day analysis data available"

        lines = []
        days_order = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]

        for day in days_order:
            day_data = day_analysis.get(day, {})
            if not day_data:
                continue

            draws = day_data.get("total_draws", day_data.get("draw_count", 0))
            msg = day_data.get("message", "")
            hot = day_data.get("hot_numbers", [])

            if draws > 0:
                line = f"- **{day}:** {draws} draws"
                if hot:
                    line += f" | Hot: {hot[:6]}"
                if msg:
                    line += f" | {msg}"
                lines.append(line)
            elif msg:
                lines.append(f"- **{day}:** {msg}")

        return "\n".join(lines) if lines else "No day analysis data"

    def _format_temporal_day_of_week(self, by_dow: Dict) -> str:
        """Format temporal patterns by day of week."""
        if not by_dow:
            return "No day-of-week temporal data available"

        lines = []
        for day, data in by_dow.items():
            if isinstance(data, dict):
                draws = data.get("total_draws", 0)
                hot = data.get("hot_numbers", [])
                lines.append(f"- **{day}:** {draws} draws | Hot: {hot[:6]}")

        return "\n".join(lines) if lines else "No data"

    def _format_consistent_performers(self, performers: List) -> str:
        """Format year-over-year consistent performers."""
        if not performers:
            return "No consistent performer data available"

        lines = []
        for p in performers[:10]:
            if isinstance(p, dict):
                lines.append(
                    f"- Number {p.get('number', '?')}: "
                    f"avg freq {p.get('average_frequency', 0):.1f}, "
                    f"consistency {p.get('consistency_score', 0):.3f}, "
                    f"appeared in {p.get('years_appeared', 0)} years"
                )

        return "\n".join(lines) if lines else "No data"

    def _format_high_performers(self, performers: List) -> str:
        """Format distinct high performers by year."""
        if not performers:
            return "No high performer data available"

        lines = []
        for p in performers[:10]:
            if isinstance(p, dict):
                lines.append(
                    f"- Number {p.get('number', '?')} in {p.get('year', '?')}: "
                    f"freq {p.get('frequency', 0)}, "
                    f"{p.get('improvement_over_average', 0):.1f}% above average"
                )

        return "\n".join(lines) if lines else "No data"

    def _format_historical_observations(self, observations: Dict) -> str:
        """Format historical observations and insights."""
        if not observations:
            return "No historical observation data available"

        sections = []

        # Highly frequent numbers
        hf = observations.get("highly_frequent_numbers", [])
        if hf:
            sections.append("**Highly Frequent Numbers:**")
            for item in hf[:10]:
                if isinstance(item, dict):
                    obs_text = item.get(
                        "observation", f"Number {item.get('number', '?')}"
                    )
                    sections.append(f"- {obs_text}")

        # Common repeating patterns
        rp = observations.get("common_repeating_patterns", [])
        if rp:
            sections.append("\n**Common Repeating Patterns:**")
            for item in rp[:8]:
                if isinstance(item, dict):
                    sections.append(f"- {item.get('observation', '')}")

        # Year-to-year insights
        yty = observations.get("year_to_year_insights", [])
        if yty:
            sections.append("\n**Year-to-Year Insights:**")
            for item in yty[:8]:
                if isinstance(item, dict):
                    sections.append(f"- {item.get('observation', '')}")

        # Consistency insights
        ci = observations.get("consistency_insights", [])
        if ci:
            sections.append("\n**Consistency Insights:**")
            for item in ci[:8]:
                if isinstance(item, dict):
                    sections.append(f"- {item.get('observation', '')}")

        # Temporal insights
        ti = observations.get("temporal_insights", [])
        if ti:
            sections.append("\n**Temporal/Seasonal Insights:**")
            for item in ti[:8]:
                if isinstance(item, dict):
                    sections.append(f"- {item.get('observation', '')}")

        return "\n".join(sections) if sections else "No historical observations"

    def _build_analysis_prompt(
        self,
        game_type: str,
        total_draws: int,
        date_range: Dict,
        predictions: Dict,
        frequency_analysis: Dict,
        pattern_analysis: Dict,
        temporal_analysis: Dict,
    ) -> str:
        """
        Build comprehensive analysis prompt for AI.

        Args:
            game_type: Type of lottery game
            total_draws: Number of draws analyzed
            date_range: Start and end dates
            predictions: All prediction sets
            frequency_analysis: Frequency statistics
            pattern_analysis: Pattern analysis data
            temporal_analysis: Temporal trend data

        Returns:
            Formatted prompt string
        """
        # Safety check for total_draws
        if total_draws <= 0:
            logger.warning(
                f"Invalid total_draws value: {total_draws}. Using 1 as default."
            )
            total_draws = 1

        # Extract max number from game type (e.g., "6/58" -> 58)
        max_num = int(game_type.split("/")[-1])
        numbers_to_pick = int(game_type.split("/")[0].split()[-1])

        # Format top predictions from different methods
        top_preds = predictions.get("top_predictions", [])[:5]
        winning_preds = predictions.get("winning_predictions", [])[:5]
        pattern_preds = predictions.get("pattern_based_predictions", [])[:5]
        ultimate_preds = predictions.get("ultimate_predictions", [])[:5]

        # Format frequency data
        most_frequent = frequency_analysis.get("most_common", [])[:15]
        least_frequent = frequency_analysis.get("least_common", [])[:15]

        # Format pattern insights
        consecutive_patterns = pattern_analysis.get("consecutive_patterns", {})
        even_odd_dist = pattern_analysis.get("even_odd_distribution", {})
        sum_ranges = pattern_analysis.get("sum_ranges", {})
        high_low_balance = pattern_analysis.get("high_low_balance", {})

        # Format temporal analysis
        day_patterns = temporal_analysis.get("by_day", {})
        recent_trends = temporal_analysis.get("recent_trends", {})

        prompt = f"""# PCSO Lottery Statistical Analysis Request

## 📊 LOTTERY GAME INFORMATION

**Game Type:** {game_type} (Philippine PCSO)  
**Analysis Period:** {date_range.get("start", "N/A")} to {date_range.get("end", "N/A")}  
**Total Historical Draws:** {total_draws:,} draws  
**Number Range:** 1 to {max_num}  
**Numbers Per Draw:** {numbers_to_pick} numbers  

---

## 📈 COMPREHENSIVE STATISTICAL DATA

### 1️⃣ FREQUENCY ANALYSIS

**"Hot Numbers" - Most Frequently Drawn (Top 15):**
{self._format_frequency_list(most_frequent)}

**"Cold Numbers" - Least Frequently Drawn (Top 15):**
{self._format_frequency_list(least_frequent)}

**Statistical Notes:**
- Expected avg frequency per number: {((total_draws * numbers_to_pick / max_num) if total_draws > 0 else 0):.1f} appearances
- Actual frequency range: {least_frequent[0][1] if least_frequent else "N/A"} to {most_frequent[0][1] if most_frequent else "N/A"}

---

### 2️⃣ PATTERN DISTRIBUTION ANALYSIS

**Consecutive Numbers:**
- Total occurrences: {consecutive_patterns.get("total_occurrences", 0):,} times
- Frequency: {((consecutive_patterns.get("total_occurrences", 0) / total_draws * 100) if total_draws > 0 else 0):.1f}% of draws

**Even/Odd Distribution:**
- Average Even numbers: {even_odd_dist.get("ratios", {}).get("even", 0):.1f}%
- Average Odd numbers: {even_odd_dist.get("ratios", {}).get("odd", 0):.1f}%

**High/Low Number Balance:**
- High numbers (>{max_num // 2}): {high_low_balance.get("ratios", {}).get("high", 0):.1f}%
- Low numbers (≤{max_num // 2}): {high_low_balance.get("ratios", {}).get("low", 0):.1f}%

**Sum Range Analysis:**
- Average sum of numbers: {sum_ranges.get("average_sum", 0):.1f}
- Sum typically ranges: {sum_ranges.get("min_sum", 0)} to {sum_ranges.get("max_sum", 0)}

---

### 3️⃣ TEMPORAL ANALYSIS

**Day of Week Patterns:**
{self._format_day_patterns(day_patterns)}

**Recent Trends (Last 30 draws):**
{self._format_recent_trends(recent_trends)}

---

### 4️⃣ ALGORITHMIC PREDICTIONS

Our system uses 4 different statistical algorithms. Here are their top predictions:

**Algorithm 1: Frequency-Based (Weighted by recent performance)**
{self._format_prediction_list_detailed(top_preds)}

**Algorithm 2: Winning Pattern Analysis (Based on actual winner characteristics)**
{self._format_prediction_list_detailed(winning_preds)}

**Algorithm 3: Pattern-Based (Considers distribution patterns)**
{self._format_prediction_list_detailed(pattern_preds)}

**Algorithm 4: Ultimate Multi-Dimensional (Combines all factors)**
{self._format_prediction_list_detailed(ultimate_preds)}

---

## 🎯 YOUR ANALYTICAL TASK

Please provide a comprehensive analysis in the following format:

### 1. EXECUTIVE SUMMARY (3-4 paragraphs)
Provide a high-level overview of the most important findings from this {total_draws:,} draw dataset. What are the key statistical patterns? Any surprising trends? What makes this game's distribution unique?

### 2. STATISTICAL INSIGHTS (Detailed Analysis)

**a) Frequency Analysis Interpretation:**
- What do the hot/cold number patterns tell us?
- Are there any statistically significant deviations?
- How does actual vs expected frequency compare?

**b) Pattern & Distribution Analysis:**
- Analysis of even/odd and high/low balance
- Significance of consecutive number occurrences
- Sum range patterns and what they indicate

**c) Temporal Trends:**
- Day-of-week patterns and their relevance
- Recent trend analysis - any shifts in patterns?

### 3. AI-RECOMMENDED TOP 5 NUMBER COMBINATIONS

Based on ALL the statistical data provided above, generate your own 5 combinations that you believe have good statistical backing. For each combination:

**Format:**
🎲 **Combination 1:** [number, number, number, number, number, number]
   - **Reasoning:** Explain why this combination based on the statistics
   - **Key factors:** (e.g., hot numbers, balanced distribution, recent trends)
   
(Repeat for all 5 combinations)

**Your combinations should:**
- Be {numbers_to_pick} numbers between 1 and {max_num}
- Consider frequency, patterns, and temporal trends
- Have balanced even/odd and high/low distribution when possible
- Be clearly distinct from each other
- Have solid statistical reasoning

### 4. CONFIDENCE ASSESSMENT
Rate each of your 5 combinations on a scale of 1-5 stars (⭐) based on statistical strength.

### 5. IMPORTANT DISCLAIMER ⚠️
Remind users about the random nature of lottery draws and responsible gaming.

---

**REMEMBER:** 
- Be specific and data-driven in your analysis
- Reference actual numbers from the statistics provided
- Make your reasoning transparent and educational
- Format your response in clean, readable markdown
- Balance statistical rigor with accessibility

Please proceed with your comprehensive analysis.
"""

        return prompt

    def _format_frequency_list(self, freq_list: List) -> str:
        """Format frequency data for prompt."""
        if not freq_list:
            return "No data available"

        lines = []
        for num, count in freq_list:
            lines.append(f"- Number {num}: {count} times")

        return "\n".join(lines) if lines else "No data available"

    def _format_prediction_list(self, pred_list: List) -> str:
        """Format prediction combinations for prompt."""
        if not pred_list:
            return "No predictions available"

        lines = []
        for i, pred in enumerate(pred_list, 1):
            numbers = pred.get("numbers", [])
            score = pred.get("score", 0)
            lines.append(f"   - Set {i}: {sorted(numbers)} (Score: {score:.3f})")

        return "\n".join(lines) if lines else "No predictions available"

    def _format_prediction_list_detailed(self, pred_list: List) -> str:
        """Format prediction combinations with detailed info for prompt."""
        if not pred_list:
            return "No predictions available"

        lines = []
        for i, pred in enumerate(pred_list, 1):
            numbers = sorted(pred.get("numbers", []))
            score = pred.get("score", 0)

            # Calculate some quick stats
            even_count = sum(1 for n in numbers if n % 2 == 0)
            odd_count = len(numbers) - even_count

            lines.append(
                f"   {i}. {numbers}\n"
                f"      Score: {score:.3f} | Even/Odd: {even_count}/{odd_count}"
            )

        return "\n".join(lines) if lines else "No predictions available"

    def _format_day_patterns(self, day_patterns: Dict) -> str:
        """Format day-of-week pattern data."""
        if not day_patterns:
            return "No day pattern data available"

        days = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]
        lines = []

        for day in days:
            day_data = day_patterns.get(day, {})
            draw_count = day_data.get("draw_count", 0)
            if draw_count > 0:
                hot_nums_data = day_data.get("hot_numbers", [])
                # Ensure it's a list before slicing
                if isinstance(hot_nums_data, list):
                    hot_nums = hot_nums_data[:5]
                    lines.append(
                        f"- **{day}:** {draw_count} draws | "
                        f"Hot: {hot_nums if hot_nums else 'N/A'}"
                    )

        return "\n".join(lines) if lines else "No day pattern data"

    def _format_recent_trends(self, recent_trends: Dict) -> str:
        """Format recent trend analysis."""
        if not recent_trends:
            return "No recent trend data available"

        lines = []

        # Most recent hot numbers
        hot_nums_data = recent_trends.get("hot_numbers", [])
        # Ensure it's a list before slicing
        if isinstance(hot_nums_data, list):
            hot_nums = hot_nums_data[:10]
            if hot_nums:
                lines.append(f"- **Trending Hot:** {hot_nums}")

        # Most recent cold numbers
        cold_nums_data = recent_trends.get("cold_numbers", [])
        # Ensure it's a list before slicing
        if isinstance(cold_nums_data, list):
            cold_nums = cold_nums_data[:10]
            if cold_nums:
                lines.append(f"- **Trending Cold:** {cold_nums}")

        # Recent pattern shifts
        if "pattern_shift" in recent_trends:
            lines.append(f"- **Pattern Shift:** {recent_trends['pattern_shift']}")

        return "\n".join(lines) if lines else "No significant recent trends detected"


def test_ollama_connection():
    """Test function to verify Ollama connectivity."""
    try:
        analyzer = AIAnalyzer()
        status = analyzer.check_ollama_status()

        print("=" * 60)
        print("Ollama Status Check")
        print("=" * 60)
        print(f"Running: {status.get('running')}")
        print(f"Configured Model: {status.get('configured_model')}")
        print(f"Model Available: {status.get('model_available')}")

        if status.get("available_models"):
            print("\nAvailable Models:")
            for model in status["available_models"]:
                print(f"  - {model}")

        if not status.get("running"):
            print(f"\nError: {status.get('error')}")
            print("\nTo start Ollama, run: ollama serve")

        return status

    except Exception as e:
        print(f"Connection test failed: {str(e)}")
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    test_ollama_connection()
