"""
Lottery Data Analysis Module
Analyzes lottery draw results and calculates probability-based predictions.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from collections import Counter, defaultdict
from itertools import combinations
from datetime import datetime


class LotteryAnalyzer:
    """Analyzes lottery data and generates probability-based predictions."""

    DAYS_OF_WEEK = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

    def __init__(self, data: Dict):
        """
        Initialize analyzer with lottery data.

        Args:
            data: Dictionary containing lottery results
        """
        self.data = data
        self.game_type = data['game_type']
        # Sort results by date (newest first)
        self.results = sorted(
            data['results'],
            key=lambda x: datetime.strptime(x['date'], '%m/%d/%Y'),
            reverse=True
        )
        self.df = self._create_dataframe()

        # Extract max number from game type (e.g., "Lotto 6/42" -> 42)
        self.max_number = int(self.game_type.split('/')[-1])
        self.numbers_to_pick = int(self.game_type.split('/')[0].split()[-1])

    def _create_dataframe(self) -> pd.DataFrame:
        """Create pandas DataFrame from results."""
        if not self.results:
            return pd.DataFrame()

        df = pd.DataFrame(self.results)
        df['date'] = pd.to_datetime(df['date'])
        return df

    def get_overall_statistics(self) -> Dict:
        """
        Calculate overall statistics for all draws.

        Returns:
            Dictionary containing various statistics
        """
        if self.df.empty:
            return {}

        # Flatten all numbers
        all_numbers = [num for result in self.results for num in result['numbers']]
        number_freq = Counter(all_numbers)

        # Calculate statistics
        stats = {
            'total_draws': len(self.results),
            'date_range': {
                'start': self.data['start_date'],
                'end': self.data['end_date']
            },
            'most_frequent_numbers': sorted(
                number_freq.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10],
            'least_frequent_numbers': sorted(
                number_freq.items(),
                key=lambda x: x[1]
            )[:10],
            'number_frequency': dict(number_freq),
            'average_frequency': np.mean(list(number_freq.values())),
            'hot_numbers': self._get_hot_numbers(number_freq, top_n=10),
            'cold_numbers': self._get_cold_numbers(number_freq, top_n=10),
            'even_odd_analysis': self._analyze_even_odd(),
            'high_low_analysis': self._analyze_high_low(),
            'consecutive_analysis': self._analyze_consecutive_numbers(),
            'sum_analysis': self._analyze_sum_ranges(),
            'winner_analysis': self.get_winner_analysis()
        }

        return stats

    def get_day_specific_analysis(self, day: str) -> Dict:
        """
        Analyze draws for a specific day of the week.

        Args:
            day: Day of the week (e.g., 'Monday')

        Returns:
            Dictionary containing day-specific statistics
        """
        if day not in self.DAYS_OF_WEEK:
            raise ValueError(f"Invalid day. Must be one of: {self.DAYS_OF_WEEK}")

        # Filter results for specific day
        day_results = [r for r in self.results if r['day_of_week'] == day]

        if not day_results:
            return {'day': day, 'total_draws': 0, 'message': f'No draws found for {day}'}

        # Flatten numbers for this day
        day_numbers = [num for result in day_results for num in result['numbers']]
        number_freq = Counter(day_numbers)

        stats = {
            'day': day,
            'total_draws': len(day_results),
            'most_frequent_numbers': sorted(
                number_freq.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10],
            'number_frequency': dict(number_freq),
            'hot_numbers': self._get_hot_numbers(number_freq, top_n=6),
            'predicted_combinations': self._generate_predictions_for_day(day_results, top_n=5)
        }

        return stats

    def get_all_days_analysis(self) -> Dict:
        """
        Get analysis for all days of the week.

        Returns:
            Dictionary with analysis for each day
        """
        return {day: self.get_day_specific_analysis(day) for day in self.DAYS_OF_WEEK}

    def _get_hot_numbers(self, freq: Counter, top_n: int = 10) -> List[int]:
        """Get the most frequently drawn numbers."""
        return [num for num, _ in freq.most_common(top_n)]

    def _get_cold_numbers(self, freq: Counter, top_n: int = 10) -> List[int]:
        """Get the least frequently drawn numbers."""
        return [num for num, _ in freq.most_common()[:-top_n-1:-1]]

    def _analyze_even_odd(self) -> Dict:
        """Analyze even/odd number distribution."""
        even_odd_patterns = defaultdict(int)

        for result in self.results:
            even_count = sum(1 for num in result['numbers'] if num % 2 == 0)
            odd_count = len(result['numbers']) - even_count
            pattern = f"{even_count}E-{odd_count}O"
            even_odd_patterns[pattern] += 1

        return {
            'patterns': dict(even_odd_patterns),
            'most_common_pattern': max(even_odd_patterns.items(), key=lambda x: x[1])[0]
        }

    def _analyze_high_low(self) -> Dict:
        """Analyze high/low number distribution."""
        mid_point = self.max_number // 2
        high_low_patterns = defaultdict(int)

        for result in self.results:
            low_count = sum(1 for num in result['numbers'] if num <= mid_point)
            high_count = len(result['numbers']) - low_count
            pattern = f"{low_count}L-{high_count}H"
            high_low_patterns[pattern] += 1

        return {
            'patterns': dict(high_low_patterns),
            'most_common_pattern': max(high_low_patterns.items(), key=lambda x: x[1])[0],
            'mid_point': mid_point
        }

    def _analyze_consecutive_numbers(self) -> Dict:
        """Analyze consecutive number patterns."""
        consecutive_stats = []

        for result in self.results:
            sorted_nums = sorted(result['numbers'])
            consecutive_count = 0

            for i in range(len(sorted_nums) - 1):
                if sorted_nums[i+1] - sorted_nums[i] == 1:
                    consecutive_count += 1

            consecutive_stats.append(consecutive_count)

        return {
            'average_consecutive': np.mean(consecutive_stats),
            'max_consecutive': max(consecutive_stats),
            'draws_with_consecutive': sum(1 for c in consecutive_stats if c > 0),
            'percentage_with_consecutive': (sum(1 for c in consecutive_stats if c > 0) / len(consecutive_stats)) * 100
        }

    def _analyze_sum_ranges(self) -> Dict:
        """Analyze sum of numbers in draws."""
        sums = [sum(result['numbers']) for result in self.results]

        return {
            'average_sum': np.mean(sums),
            'min_sum': min(sums),
            'max_sum': max(sums),
            'median_sum': np.median(sums),
            'std_dev': np.std(sums)
        }

    def generate_top_predictions(self, top_n: int = 5) -> List[Dict]:
        """
        Generate top N predicted combinations based on overall analysis.

        Args:
            top_n: Number of predictions to generate

        Returns:
            List of predicted combinations with scores
        """
        # Get frequency of all numbers
        all_numbers = [num for result in self.results for num in result['numbers']]
        number_freq = Counter(all_numbers)

        # Calculate weighted scores for each number
        max_freq = max(number_freq.values())
        number_scores = {
            num: freq / max_freq for num, freq in number_freq.items()
        }

        # Add numbers that haven't appeared (cold numbers might be due)
        for num in range(1, self.max_number + 1):
            if num not in number_scores:
                number_scores[num] = 0.1  # Small weight for missing numbers

        # Generate combinations using weighted random selection
        predictions = []
        seen_combinations = set()

        # Get recent patterns
        recent_even_odd = self._get_recent_pattern_preference('even_odd')
        recent_high_low = self._get_recent_pattern_preference('high_low')

        attempts = 0
        max_attempts = top_n * 100

        while len(predictions) < top_n and attempts < max_attempts:
            attempts += 1

            # Generate a combination favoring hot numbers with some randomness
            numbers = list(number_scores.keys())
            weights = list(number_scores.values())

            # Add randomness to avoid always picking the same numbers
            adjusted_weights = [w + np.random.random() * 0.3 for w in weights]

            chosen = set()
            for _ in range(self.numbers_to_pick):
                if not numbers:
                    break

                # Select number based on weights
                probs = np.array(adjusted_weights) / sum(adjusted_weights)
                idx = np.random.choice(len(numbers), p=probs)
                chosen.add(numbers[idx])

                # Remove selected number
                numbers.pop(idx)
                adjusted_weights.pop(idx)

            if len(chosen) == self.numbers_to_pick:
                combo = tuple(sorted(chosen))

                if combo not in seen_combinations:
                    seen_combinations.add(combo)

                    # Calculate confidence score
                    score = self._calculate_combination_score(combo, number_scores)

                    predictions.append({
                        'numbers': list(combo),
                        'confidence_score': round(score, 2),
                        'analysis': self._analyze_combination(combo)
                    })

        # Sort by confidence score
        predictions.sort(key=lambda x: x['confidence_score'], reverse=True)

        return predictions[:top_n]

    def _generate_predictions_for_day(self, day_results: List[Dict], top_n: int = 5) -> List[Dict]:
        """Generate predictions specific to a day of the week."""
        if not day_results:
            return []

        # Get frequency for this day
        day_numbers = [num for result in day_results for num in result['numbers']]
        number_freq = Counter(day_numbers)

        max_freq = max(number_freq.values()) if number_freq else 1
        number_scores = {
            num: freq / max_freq for num, freq in number_freq.items()
        }

        # Fill in missing numbers
        for num in range(1, self.max_number + 1):
            if num not in number_scores:
                number_scores[num] = 0.1

        # Generate combinations
        predictions = []
        seen_combinations = set()
        attempts = 0
        max_attempts = top_n * 100

        while len(predictions) < top_n and attempts < max_attempts:
            attempts += 1

            numbers = list(number_scores.keys())
            weights = list(number_scores.values())
            adjusted_weights = [w + np.random.random() * 0.3 for w in weights]

            chosen = set()
            for _ in range(self.numbers_to_pick):
                if not numbers:
                    break

                probs = np.array(adjusted_weights) / sum(adjusted_weights)
                idx = np.random.choice(len(numbers), p=probs)
                chosen.add(numbers[idx])

                numbers.pop(idx)
                adjusted_weights.pop(idx)

            if len(chosen) == self.numbers_to_pick:
                combo = tuple(sorted(chosen))

                if combo not in seen_combinations:
                    seen_combinations.add(combo)
                    score = self._calculate_combination_score(combo, number_scores)

                    predictions.append({
                        'numbers': list(combo),
                        'confidence_score': round(score, 2)
                    })

        predictions.sort(key=lambda x: x['confidence_score'], reverse=True)
        return predictions[:top_n]

    def _calculate_combination_score(self, combo: Tuple, number_scores: Dict) -> float:
        """Calculate a confidence score for a combination."""
        # Base score from number frequencies
        base_score = sum(number_scores.get(num, 0) for num in combo) / len(combo)

        # Bonus for balanced even/odd
        even_count = sum(1 for num in combo if num % 2 == 0)
        balance_bonus = 1.0 - abs(even_count - len(combo)/2) / len(combo)

        # Bonus for spread across range
        spread = (max(combo) - min(combo)) / self.max_number
        spread_bonus = spread * 0.5

        total_score = (base_score * 0.6) + (balance_bonus * 0.2) + (spread_bonus * 0.2)

        return min(total_score * 100, 100)  # Scale to 0-100

    def _analyze_combination(self, combo: Tuple) -> Dict:
        """Analyze a combination for various patterns."""
        even_count = sum(1 for num in combo if num % 2 == 0)
        odd_count = len(combo) - even_count

        mid_point = self.max_number // 2
        low_count = sum(1 for num in combo if num <= mid_point)
        high_count = len(combo) - low_count

        sorted_combo = sorted(combo)
        consecutive = sum(
            1 for i in range(len(sorted_combo) - 1)
            if sorted_combo[i+1] - sorted_combo[i] == 1
        )

        return {
            'even_odd': f"{even_count}E-{odd_count}O",
            'high_low': f"{low_count}L-{high_count}H",
            'sum': int(sum(combo)),  # Convert to native int
            'consecutive_pairs': int(consecutive)  # Convert to native int
        }

    def _get_recent_pattern_preference(self, pattern_type: str) -> str:
        """Get the most common pattern from recent draws."""
        recent_draws = self.results[-20:] if len(self.results) > 20 else self.results

        if pattern_type == 'even_odd':
            patterns = []
            for result in recent_draws:
                even_count = sum(1 for num in result['numbers'] if num % 2 == 0)
                odd_count = len(result['numbers']) - even_count
                patterns.append(f"{even_count}E-{odd_count}O")
            return Counter(patterns).most_common(1)[0][0]

        elif pattern_type == 'high_low':
            mid_point = self.max_number // 2
            patterns = []
            for result in recent_draws:
                low_count = sum(1 for num in result['numbers'] if num <= mid_point)
                high_count = len(result['numbers']) - low_count
                patterns.append(f"{low_count}L-{high_count}H")
            return Counter(patterns).most_common(1)[0][0]

        return ""

    def get_winner_analysis(self) -> Dict:
        """
        Analyze draws that had winners.

        Returns:
            Dictionary containing winner-specific statistics
        """
        # Filter results that have winners (not "0" or "N/A")
        winning_draws = [
            r for r in self.results
            if r.get('winners') and r['winners'] not in ['0', 'N/A', '0 winner', 'No winner']
        ]

        if not winning_draws:
            return {
                'total_winning_draws': 0,
                'message': 'No winning draws found in the dataset'
            }

        # Analyze winning numbers
        winning_numbers = [num for result in winning_draws for num in result['numbers']]
        winning_number_freq = Counter(winning_numbers)

        # Analyze winning dates
        winning_dates = [datetime.strptime(r['date'], '%m/%d/%Y') if isinstance(r['date'], str) else r['date']
                        for r in winning_draws]
        winning_days = [r['day_of_week'] for r in winning_draws]
        winning_day_freq = Counter(winning_days)

        # Analyze winning months
        winning_months = [d.month for d in winning_dates]
        winning_month_freq = Counter(winning_months)

        # Analyze jackpot amounts (if numeric)
        jackpot_amounts = []
        for r in winning_draws:
            jackpot = r.get('jackpot', 'N/A')
            if jackpot and jackpot != 'N/A':
                # Try to extract numeric value
                try:
                    # Remove commas and PHP symbol
                    clean_jackpot = str(jackpot).replace(',', '').replace('₱', '').replace('PHP', '').strip()
                    amount = float(clean_jackpot)
                    jackpot_amounts.append(amount)
                except (ValueError, AttributeError):
                    pass

        analysis = {
            'total_winning_draws': len(winning_draws),
            'win_rate': round((len(winning_draws) / len(self.results)) * 100, 2),

            # Most frequent winning numbers
            'most_frequent_winning_numbers': sorted(
                winning_number_freq.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10],

            # Hot winning numbers
            'hot_winning_numbers': self._get_hot_numbers(winning_number_freq, top_n=10),

            # Day of week analysis for wins
            'winning_days_frequency': dict(winning_day_freq),
            'best_winning_days': sorted(
                winning_day_freq.items(),
                key=lambda x: x[1],
                reverse=True
            )[:3],

            # Month analysis for wins
            'winning_months_frequency': dict(winning_month_freq),
            'best_winning_months': sorted(
                winning_month_freq.items(),
                key=lambda x: x[1],
                reverse=True
            )[:3],

            # Winning patterns
            'winning_even_odd_patterns': self._analyze_pattern_for_draws(winning_draws, 'even_odd'),
            'winning_high_low_patterns': self._analyze_pattern_for_draws(winning_draws, 'high_low'),

            # Jackpot statistics (if available)
            'jackpot_stats': {
                'count': len(jackpot_amounts),
                'average': round(np.mean(jackpot_amounts), 2) if jackpot_amounts else 0,
                'min': round(min(jackpot_amounts), 2) if jackpot_amounts else 0,
                'max': round(max(jackpot_amounts), 2) if jackpot_amounts else 0,
            } if jackpot_amounts else None,

            # Probability predictions
            'next_win_probability': self._predict_next_win_probability(winning_draws)
        }

        return analysis

    def _analyze_pattern_for_draws(self, draws: List[Dict], pattern_type: str) -> Dict:
        """Analyze even/odd or high/low patterns for specific draws."""
        patterns = defaultdict(int)

        if pattern_type == 'even_odd':
            for result in draws:
                even_count = sum(1 for num in result['numbers'] if num % 2 == 0)
                odd_count = len(result['numbers']) - even_count
                pattern = f"{even_count}E-{odd_count}O"
                patterns[pattern] += 1

        elif pattern_type == 'high_low':
            mid_point = self.max_number // 2
            for result in draws:
                low_count = sum(1 for num in result['numbers'] if num <= mid_point)
                high_count = len(result['numbers']) - low_count
                pattern = f"{low_count}L-{high_count}H"
                patterns[pattern] += 1

        if patterns:
            most_common = max(patterns.items(), key=lambda x: x[1])
            return {
                'patterns': dict(patterns),
                'most_common_pattern': most_common[0],
                'most_common_count': most_common[1]
            }
        return {'patterns': {}, 'most_common_pattern': None}

    def _predict_next_win_probability(self, winning_draws: List[Dict]) -> Dict:
        """
        Predict probability patterns for next potential win.

        Returns:
            Dictionary with probability predictions
        """
        if not winning_draws:
            return {}

        # Analyze time gaps between wins
        winning_dates = []
        for r in winning_draws:
            try:
                if isinstance(r['date'], str):
                    date = datetime.strptime(r['date'], '%m/%d/%Y')
                else:
                    date = r['date']
                winning_dates.append(date)
            except (ValueError, KeyError):
                continue

        winning_dates.sort()

        # Calculate days between wins
        if len(winning_dates) > 1:
            gaps = [(winning_dates[i+1] - winning_dates[i]).days
                    for i in range(len(winning_dates) - 1)]

            avg_gap = np.mean(gaps)
            median_gap = np.median(gaps)
            std_gap = np.std(gaps)

            # Predict next win window
            last_win = winning_dates[-1]
            days_since_last_win = (datetime.now() - last_win).days

            # Calculate probability zones
            expected_next_win = int(avg_gap)
            early_window = max(1, int(avg_gap - std_gap))
            late_window = int(avg_gap + std_gap)

            return {
                'average_days_between_wins': round(avg_gap, 1),
                'median_days_between_wins': round(median_gap, 1),
                'std_dev_days': round(std_gap, 1),
                'last_win_date': last_win.strftime('%Y-%m-%d'),
                'days_since_last_win': days_since_last_win,
                'expected_next_win_in_days': expected_next_win,
                'early_win_window': f"{early_window} days",
                'late_win_window': f"{late_window} days",
                'probability_status': self._get_win_probability_status(
                    days_since_last_win, avg_gap, std_gap
                )
            }

        return {'message': 'Insufficient data for prediction'}

    def _get_win_probability_status(self, days_since: int, avg_gap: float, std_dev: float) -> str:
        """Determine current probability status for a win."""
        if days_since < avg_gap - std_dev:
            return "Low - Too soon since last win"
        elif days_since < avg_gap:
            return "Medium - Approaching average window"
        elif days_since < avg_gap + std_dev:
            return "High - Within expected window"
        else:
            return "Very High - Overdue for a win"

    def generate_winning_predictions(self, top_n: int = 5) -> List[Dict]:
        """
        Generate predictions based specifically on winning draw patterns.

        Args:
            top_n: Number of predictions to generate

        Returns:
            List of predicted combinations optimized for wins
        """
        # Get winning draws
        winning_draws = [
            r for r in self.results
            if r.get('winners') and r['winners'] not in ['0', 'N/A', '0 winner', 'No winner']
        ]

        if not winning_draws:
            # Fall back to regular predictions
            return self.generate_top_predictions(top_n)

        # Analyze winning numbers with higher weight
        winning_numbers = [num for result in winning_draws for num in result['numbers']]
        winning_freq = Counter(winning_numbers)

        # Calculate scores with emphasis on winning frequency
        max_freq = max(winning_freq.values()) if winning_freq else 1
        number_scores = {
            num: (freq / max_freq) * 1.5  # 1.5x weight for winning numbers
            for num, freq in winning_freq.items()
        }

        # Add other numbers with lower scores
        all_numbers = [num for result in self.results for num in result['numbers']]
        all_freq = Counter(all_numbers)
        for num in range(1, self.max_number + 1):
            if num not in number_scores:
                number_scores[num] = (all_freq.get(num, 0) / max(all_freq.values())) * 0.5

        # Generate combinations
        predictions = []
        seen_combinations = set()
        attempts = 0
        max_attempts = top_n * 100

        while len(predictions) < top_n and attempts < max_attempts:
            attempts += 1

            numbers = list(number_scores.keys())
            weights = list(number_scores.values())
            adjusted_weights = [w + np.random.random() * 0.2 for w in weights]

            chosen = set()
            for _ in range(self.numbers_to_pick):
                if not numbers:
                    break

                probs = np.array(adjusted_weights) / sum(adjusted_weights)
                idx = np.random.choice(len(numbers), p=probs)
                chosen.add(numbers[idx])

                numbers.pop(idx)
                adjusted_weights.pop(idx)

            if len(chosen) == self.numbers_to_pick:
                combo = tuple(sorted(chosen))

                if combo not in seen_combinations:
                    seen_combinations.add(combo)
                    score = self._calculate_winning_score(combo, number_scores, winning_draws)

                    predictions.append({
                        'numbers': list(combo),
                        'win_probability_score': round(score, 2),
                        'analysis': self._analyze_combination(combo),
                        'prediction_type': 'Winner-Optimized'
                    })

        predictions.sort(key=lambda x: x['win_probability_score'], reverse=True)
        return predictions[:top_n]

    def _calculate_winning_score(self, combo: Tuple, number_scores: Dict, winning_draws: List[Dict]) -> float:
        """Calculate score based on winning patterns."""
        # Base score from winning number frequencies
        base_score = sum(number_scores.get(num, 0) for num in combo) / len(combo)

        # Check if combo matches winning patterns
        winning_patterns = self._analyze_pattern_for_draws(winning_draws, 'even_odd')
        combo_even = sum(1 for num in combo if num % 2 == 0)
        combo_pattern = f"{combo_even}E-{len(combo) - combo_even}O"

        pattern_bonus = 0.3 if combo_pattern == winning_patterns.get('most_common_pattern') else 0

        # Range spread bonus
        spread = (max(combo) - min(combo)) / self.max_number
        spread_bonus = spread * 0.2

        total_score = (base_score * 0.7) + pattern_bonus + spread_bonus
        return min(total_score * 100, 100)

    def analyze_consecutive_draw_patterns(self) -> Dict:
        """
        Analyze patterns between consecutive draws to predict next draw.

        Returns:
            Dictionary with pattern analysis and predictions
        """
        if len(self.results) < 2:
            return {'message': 'Insufficient data for consecutive draw analysis'}

        patterns = {
            'number_carryover': [],  # How many numbers repeat from previous draw
            'number_gaps': [],  # Gaps between draws
            'sum_differences': [],  # Difference in sums
            'pattern_transitions': defaultdict(int),  # Even/odd pattern changes
            'new_numbers_per_draw': []  # How many new numbers appear
        }

        # Analyze consecutive draws
        for i in range(len(self.results) - 1):
            current_draw = self.results[i]
            next_draw = self.results[i + 1]

            current_nums = set(current_draw['numbers'])
            next_nums = set(next_draw['numbers'])

            # Count carryover (repeated numbers)
            carryover = len(current_nums & next_nums)
            patterns['number_carryover'].append(carryover)

            # Count new numbers
            new_numbers = len(next_nums - current_nums)
            patterns['new_numbers_per_draw'].append(new_numbers)

            # Sum difference
            sum_diff = abs(sum(next_draw['numbers']) - sum(current_draw['numbers']))
            patterns['sum_differences'].append(sum_diff)

            # Pattern transitions (even/odd)
            curr_even = sum(1 for n in current_nums if n % 2 == 0)
            next_even = sum(1 for n in next_nums if n % 2 == 0)
            curr_pattern = f"{curr_even}E-{len(current_nums) - curr_even}O"
            next_pattern = f"{next_even}E-{len(next_nums) - next_even}O"
            transition = f"{curr_pattern} → {next_pattern}"
            patterns['pattern_transitions'][transition] += 1

        # Calculate statistics
        analysis = {
            'average_carryover': round(float(np.mean(patterns['number_carryover'])), 2),
            'most_common_carryover': int(Counter(patterns['number_carryover']).most_common(1)[0][0]),
            'average_new_numbers': round(float(np.mean(patterns['new_numbers_per_draw'])), 2),
            'average_sum_difference': round(float(np.mean(patterns['sum_differences'])), 2),
            'most_common_pattern_transition': max(patterns['pattern_transitions'].items(), key=lambda x: x[1])[0],
            'carryover_distribution': {int(k): int(v) for k, v in Counter(patterns['number_carryover']).items()},
            'pattern_transitions': {k: int(v) for k, v in patterns['pattern_transitions'].items()}
        }

        # Get most recent draw for prediction context
        latest_draw = self.results[0]  # Assuming most recent is first
        analysis['latest_draw'] = {
            'date': latest_draw['date'],
            'numbers': [int(n) for n in latest_draw['numbers']],  # Convert to native int
            'sum': int(sum(latest_draw['numbers']))
        }

        return analysis

    def generate_pattern_based_prediction(self, top_n: int = 5) -> List[Dict]:
        """
        Generate predictions based on consecutive draw patterns.

        Args:
            top_n: Number of predictions to generate

        Returns:
            List of pattern-based predictions
        """
        pattern_analysis = self.analyze_consecutive_draw_patterns()

        if 'message' in pattern_analysis:
            return []

        # Get the latest draw
        latest_draw = self.results[0]
        latest_numbers = set(latest_draw['numbers'])

        # Get frequency data
        all_numbers = [num for result in self.results for num in result['numbers']]
        number_freq = Counter(all_numbers)

        # Expected carryover count
        expected_carryover = int(round(pattern_analysis['average_carryover']))
        expected_new = int(round(pattern_analysis['average_new_numbers']))

        predictions = []
        seen_combinations = set()
        attempts = 0
        max_attempts = top_n * 200

        while len(predictions) < top_n and attempts < max_attempts:
            attempts += 1

            # Select numbers to carry over from latest draw
            if expected_carryover > 0 and expected_carryover <= len(latest_numbers):
                # Randomly select numbers to carry over
                carryover_nums = set(np.random.choice(list(latest_numbers),
                                                     size=min(expected_carryover, len(latest_numbers)),
                                                     replace=False))
            else:
                carryover_nums = set()

            # Fill remaining slots with new numbers based on frequency
            remaining_slots = self.numbers_to_pick - len(carryover_nums)

            # Get available numbers (excluding carryover)
            available_numbers = [n for n in range(1, self.max_number + 1) if n not in carryover_nums]
            available_freq = {n: number_freq.get(n, 0) for n in available_numbers}

            # Weighted selection for new numbers
            if available_numbers and remaining_slots > 0:
                weights = [available_freq[n] + np.random.random() * 50 for n in available_numbers]
                probs = np.array(weights) / sum(weights)

                new_nums = set(np.random.choice(available_numbers,
                                               size=min(remaining_slots, len(available_numbers)),
                                               replace=False,
                                               p=probs))
            else:
                new_nums = set()

            combo = carryover_nums | new_nums

            if len(combo) == self.numbers_to_pick:
                combo_tuple = tuple(sorted(combo))

                if combo_tuple not in seen_combinations:
                    seen_combinations.add(combo_tuple)

                    # Calculate score
                    score = self._calculate_pattern_score(combo_tuple, latest_numbers, pattern_analysis)

                    predictions.append({
                        'numbers': [int(n) for n in combo_tuple],  # Convert to native int
                        'pattern_score': round(float(score), 2),
                        'carryover_count': int(len(combo & latest_numbers)),
                        'new_count': int(len(combo - latest_numbers)),
                        'analysis': self._analyze_combination(combo_tuple),
                        'prediction_type': 'Pattern-Based'
                    })

        # Sort by score
        predictions.sort(key=lambda x: x['pattern_score'], reverse=True)

        return predictions[:top_n]

    def _calculate_pattern_score(self, combo: Tuple, latest_numbers: set, pattern_analysis: Dict) -> float:
        """Calculate score based on pattern analysis."""
        combo_set = set(combo)

        # Carryover score (how close to expected carryover)
        actual_carryover = len(combo_set & latest_numbers)
        expected_carryover = pattern_analysis['average_carryover']
        carryover_diff = abs(actual_carryover - expected_carryover)
        carryover_score = max(0, 1 - (carryover_diff / self.numbers_to_pick))

        # Frequency score
        all_numbers = [num for result in self.results for num in result['numbers']]
        number_freq = Counter(all_numbers)
        max_freq = max(number_freq.values())
        freq_score = sum(number_freq.get(num, 0) for num in combo) / (len(combo) * max_freq)

        # Pattern match score (even/odd balance)
        even_count = sum(1 for num in combo if num % 2 == 0)
        balance_score = 1.0 - abs(even_count - len(combo)/2) / len(combo)

        # Combined score
        total_score = (carryover_score * 0.4) + (freq_score * 0.3) + (balance_score * 0.3)

        return min(total_score * 100, 100)

    def get_chart_data(self) -> Dict:
        """
        Prepare data for charts and visualizations.

        Returns:
            Dictionary containing data formatted for charts
        """
        all_numbers = [num for result in self.results for num in result['numbers']]
        number_freq = Counter(all_numbers)

        # Frequency distribution
        freq_data = {
            'labels': [str(i) for i in range(1, self.max_number + 1)],
            'values': [number_freq.get(i, 0) for i in range(1, self.max_number + 1)]
        }

        # Day of week distribution
        day_counts = Counter([r['day_of_week'] for r in self.results])
        day_data = {
            'labels': self.DAYS_OF_WEEK,
            'values': [day_counts.get(day, 0) for day in self.DAYS_OF_WEEK]
        }

        # Even/Odd distribution
        even_odd = self._analyze_even_odd()
        even_odd_data = {
            'labels': list(even_odd['patterns'].keys()),
            'values': list(even_odd['patterns'].values())
        }

        # Sum distribution
        sums = [sum(result['numbers']) for result in self.results]
        sum_hist, sum_bins = np.histogram(sums, bins=20)
        sum_data = {
            'labels': [f"{int(sum_bins[i])}-{int(sum_bins[i+1])}" for i in range(len(sum_bins)-1)],
            'values': sum_hist.tolist()
        }

        return {
            'number_frequency': freq_data,
            'day_distribution': day_data,
            'even_odd_patterns': even_odd_data,
            'sum_distribution': sum_data
        }
