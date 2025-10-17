"""
Fortune Lab: Decoding the Jackpot
Main Flask Application
"""

import os
import json
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from app.modules.scraper import PCSOScraper
from app.modules.analyzer import LotteryAnalyzer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


app = Flask(__name__,
            template_folder='app/templates',
            static_folder='app/static')

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'fortune-lab-secret-key-2024')
app.config['DATA_PATH'] = 'app/data'


@app.route('/')
def index():
    """Main dashboard page."""
    # Get list of available result files
    data_path = app.config['DATA_PATH']
    result_files = []

    if os.path.exists(data_path):
        for filename in os.listdir(data_path):
            if filename.endswith('.json'):
                result_files.append(filename)

    return render_template('index.html', result_files=result_files)


@app.route('/scrape', methods=['POST'])
def scrape_data():
    """
    Endpoint to trigger data scraping.
    Expects JSON with: game_type, start_date, end_date
    """
    logger.info("Received scrape request")

    try:
        data = request.get_json()
        logger.info(f"Request data: {data}")

        game_type = data.get('game_type')
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')

        if not all([game_type, start_date_str, end_date_str]):
            logger.warning("Missing required fields in request")
            return jsonify({
                'success': False,
                'error': 'Missing required fields'
            }), 400

        # Parse dates
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        logger.info(f"Parsed dates - Start: {start_date}, End: {end_date}")

        # Validate date range
        if start_date > end_date:
            logger.warning("Invalid date range: start date is after end date")
            return jsonify({
                'success': False,
                'error': 'Start date must be before end date'
            }), 400

        # Create scraper and fetch data
        logger.info(f"Initializing scraper for {game_type}")
        scraper = PCSOScraper(headless=True)

        logger.info("Starting data scraping...")
        result = scraper.scrape_lottery_data(
            game_type=game_type,
            start_date=start_date,
            end_date=end_date,
            save_path=app.config['DATA_PATH']
        )

        logger.info(f"Scraping completed successfully. Total draws: {result['total_draws']}")

        # Check if data was loaded from cache or freshly scraped
        was_cached = result.get('cached', False)

        return jsonify({
            'success': True,
            'message': 'Data loaded from cache' if was_cached else 'Data scraped successfully',
            'filename': result['filename'],
            'total_draws': result['total_draws'],
            'cached': was_cached
        })

    except ValueError as e:
        logger.error(f"ValueError: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Invalid data: {str(e)}'
        }), 400
    except Exception as e:
        logger.error(f"Exception during scraping: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Error scraping data: {str(e)}'
        }), 500


@app.route('/analyze/<filename>')
def analyze(filename):
    """
    Run analysis and save report, then display dashboard.
    """
    try:
        # Load lottery data
        filepath = os.path.join(app.config['DATA_PATH'], filename)

        if not os.path.exists(filepath):
            return "Result file not found", 404

        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Create analyzer
        logger.info(f"Starting analysis for {filename}")
        analyzer = LotteryAnalyzer(data)

        # Get all analysis data
        overall_stats = analyzer.get_overall_statistics()
        day_analysis = analyzer.get_all_days_analysis()
        top_predictions = analyzer.generate_top_predictions(top_n=5)
        winning_predictions = analyzer.generate_winning_predictions(top_n=5)
        chart_data = analyzer.get_chart_data()

        # Save analysis report
        analysis_report = {
            'analyzed_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'source_file': filename,
            'game_type': data['game_type'],
            'date_range': {
                'start': data['start_date'],
                'end': data['end_date']
            },
            'total_draws': data['total_draws'],
            'overall_stats': overall_stats,
            'day_analysis': day_analysis,
            'top_predictions': top_predictions,
            'winning_predictions': winning_predictions,
            'chart_data': chart_data
        }

        # Save report to analysis directory
        analysis_dir = os.path.join(app.config['DATA_PATH'], 'analysis')
        os.makedirs(analysis_dir, exist_ok=True)

        # Create report filename with timestamp
        base_name = filename.replace('.json', '')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_filename = f"analysis_{base_name}_{timestamp}.json"
        report_path = os.path.join(analysis_dir, report_filename)

        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(analysis_report, f, indent=2, ensure_ascii=False)

        logger.info(f"Analysis report saved: {report_filename}")

        return render_template('dashboard.html',
                             data=data,
                             overall_stats=overall_stats,
                             day_analysis=day_analysis,
                             top_predictions=top_predictions,
                             winning_predictions=winning_predictions,
                             chart_data=chart_data,
                             filename=filename,
                             report_filename=report_filename)

    except Exception as e:
        logger.error(f"Error analyzing data: {str(e)}", exc_info=True)
        return f"Error analyzing data: {str(e)}", 500


@app.route('/api/analyze', methods=['POST'])
def api_analyze():
    """
    API endpoint to analyze a specific result file.
    Returns JSON with analysis data.
    """
    try:
        data = request.get_json()
        filename = data.get('filename')

        if not filename:
            return jsonify({
                'success': False,
                'error': 'Filename is required'
            }), 400

        # Load data
        filepath = os.path.join(app.config['DATA_PATH'], filename)

        if not os.path.exists(filepath):
            return jsonify({
                'success': False,
                'error': 'Result file not found'
            }), 404

        with open(filepath, 'r', encoding='utf-8') as f:
            lottery_data = json.load(f)

        # Create analyzer
        analyzer = LotteryAnalyzer(lottery_data)

        # Get analysis
        overall_stats = analyzer.get_overall_statistics()
        day_analysis = analyzer.get_all_days_analysis()
        top_predictions = analyzer.generate_top_predictions(top_n=5)
        winning_predictions = analyzer.generate_winning_predictions(top_n=5)
        chart_data = analyzer.get_chart_data()

        return jsonify({
            'success': True,
            'data': lottery_data,
            'overall_stats': overall_stats,
            'day_analysis': day_analysis,
            'top_predictions': top_predictions,
            'winning_predictions': winning_predictions,
            'chart_data': chart_data
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/files')
def api_list_files():
    """API endpoint to list all result files."""
    try:
        data_path = app.config['DATA_PATH']
        result_files = []

        if os.path.exists(data_path):
            for filename in os.listdir(data_path):
                if filename.endswith('.json'):
                    filepath = os.path.join(data_path, filename)

                    # Get file metadata
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    result_files.append({
                        'filename': filename,
                        'game_type': data.get('game_type'),
                        'total_draws': data.get('total_draws'),
                        'date_range': data.get('start_date') + ' to ' + data.get('end_date'),
                        'scraped_at': data.get('scraped_at')
                    })

        return jsonify({
            'success': True,
            'files': result_files
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/analysis-history/<filename>')
def get_analysis_history(filename):
    """Get all analysis reports for a specific result file."""
    try:
        analysis_dir = os.path.join(app.config['DATA_PATH'], 'analysis')

        if not os.path.exists(analysis_dir):
            return jsonify({
                'success': True,
                'reports': []
            })

        # Find all analysis reports for this file
        base_name = filename.replace('.json', '')
        pattern = f"analysis_{base_name}_*.json"

        reports = []
        for report_file in os.listdir(analysis_dir):
            if report_file.startswith(f"analysis_{base_name}_") and report_file.endswith('.json'):
                report_path = os.path.join(analysis_dir, report_file)

                # Get file metadata
                file_stat = os.stat(report_path)

                # Load report to get analyzed_at timestamp
                with open(report_path, 'r', encoding='utf-8') as f:
                    report_data = json.load(f)

                reports.append({
                    'filename': report_file,
                    'analyzed_at': report_data.get('analyzed_at'),
                    'created_at': datetime.fromtimestamp(file_stat.st_ctime).strftime('%Y-%m-%d %H:%M:%S'),
                    'size': file_stat.st_size
                })

        # Sort by analyzed_at (most recent first)
        reports.sort(key=lambda x: x['analyzed_at'], reverse=True)

        return jsonify({
            'success': True,
            'reports': reports,
            'count': len(reports)
        })

    except Exception as e:
        logger.error(f"Error getting analysis history: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/view-report/<report_filename>')
def view_report(report_filename):
    """View a specific analysis report."""
    try:
        analysis_dir = os.path.join(app.config['DATA_PATH'], 'analysis')
        report_path = os.path.join(analysis_dir, report_filename)

        if not os.path.exists(report_path):
            return "Analysis report not found", 404

        with open(report_path, 'r', encoding='utf-8') as f:
            report = json.load(f)

        # Load the original data file for context
        source_file = report.get('source_file')
        data_path = os.path.join(app.config['DATA_PATH'], source_file)

        data = {}
        if os.path.exists(data_path):
            with open(data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

        return render_template('dashboard.html',
                             data=data if data else report,
                             overall_stats=report['overall_stats'],
                             day_analysis=report['day_analysis'],
                             top_predictions=report['top_predictions'],
                             winning_predictions=report['winning_predictions'],
                             chart_data=report['chart_data'],
                             filename=source_file,
                             report_filename=report_filename,
                             analyzed_at=report['analyzed_at'],
                             is_historical=True)

    except Exception as e:
        logger.error(f"Error viewing report: {str(e)}", exc_info=True)
        return f"Error viewing report: {str(e)}", 500


@app.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return render_template('500.html'), 500


if __name__ == '__main__':
    # Create data directory if it doesn't exist
    os.makedirs(app.config['DATA_PATH'], exist_ok=True)

    # Run the app
    app.run(debug=True, host='0.0.0.0', port=5000)
