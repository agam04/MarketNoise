from django.core.management.base import BaseCommand

from api.ml.trainer import train_model
from api.ml.predictor import clear_model_cache


class Command(BaseCommand):
    help = 'Train a price-impact prediction model (Random Forest or XGBoost)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--algorithm',
            type=str,
            default='random_forest',
            choices=['random_forest', 'xgboost'],
            help='Algorithm to use (default: random_forest)',
        )

    def handle(self, *args, **options):
        algorithm = options['algorithm']

        self.stdout.write(f"\n{'='*55}")
        self.stdout.write(f"  Training {algorithm} model...")
        self.stdout.write(f"{'='*55}\n")

        result = train_model(algorithm=algorithm)

        if 'error' in result:
            self.stderr.write(self.style.ERROR(f"  {result['error']}"))
            return

        # Print results
        self.stdout.write(self.style.SUCCESS(f"  Model trained successfully!"))
        self.stdout.write(f"\n  Algorithm:      {result['algorithm']}")
        self.stdout.write(f"  Samples:        {result['samples']} total ({result['train_size']} train, {result['test_size']} test)")
        self.stdout.write(f"  Test accuracy:  {result['test_accuracy']:.1%}")
        self.stdout.write(f"  CV accuracy:    {result['cv_accuracy_mean']:.1%} (+/- {result['cv_accuracy_std']:.1%})")

        # Class distribution
        self.stdout.write(f"\n  Class distribution:")
        for cls, count in result['class_distribution'].items():
            self.stdout.write(f"    {cls:6s}: {count}")

        # Top features
        self.stdout.write(f"\n  Top features by importance:")
        for name, importance in result['top_features']:
            bar = '#' * int(importance * 50)
            self.stdout.write(f"    {name:20s} {importance:.3f} {bar}")

        # Per-class metrics
        report = result['classification_report']
        self.stdout.write(f"\n  Per-class metrics:")
        self.stdout.write(f"    {'Class':8s} {'Precision':>10s} {'Recall':>10s} {'F1':>10s}")
        for cls in ['up', 'down', 'flat']:
            if cls in report:
                r = report[cls]
                self.stdout.write(
                    f"    {cls:8s} {r['precision']:10.2f} {r['recall']:10.2f} {r['f1-score']:10.2f}"
                )

        self.stdout.write(f"\n  Model saved to: {result['model_path']}")

        # Clear cached model so next prediction loads the fresh one
        clear_model_cache()

        self.stdout.write(f"\n{'='*55}")
