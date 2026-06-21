"""
Verify all offline augmentation modules can be imported successfully.
This is a quick check before running the full pipeline.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

print("Verifying offline augmentation imports...")
print("="*60)

try:
    print("\n✓ Importing offline_data schemas...")
    from src.offline_data.offline_schema import (
        OfflineStep,
        OfflineTrajectory,
        AugmentedStep,
        AugmentedTrajectory
    )
    
    print("✓ Importing Mind2Web loader...")
    from src.offline_data.mind2web_loader import MultimodalMind2WebLoader
    
    print("✓ Importing image preprocessor...")
    from src.offline_data.image_preprocessor import (
        mask_bbox,
        compute_pixel_diff,
        compute_ssim
    )
    
    print("✓ Importing annotation processor...")
    from src.offline_data.annotation_processor import (
        parse_action_repr,
        swap_action_type
    )
    
    print("\n✓ Importing failure injection framework...")
    from src.failure_injection.injection_engine import (
        InjectionConfig,
        FailureInjector,
        InjectionPipeline
    )
    
    print("✓ Importing all 5 injector types...")
    from src.failure_injection.target_missing import TargetMissingInjector
    from src.failure_injection.misclick import MisclickInjector
    from src.failure_injection.wrong_operation import WrongOperationInjector
    from src.failure_injection.no_state_change import NoStateChangeInjector
    from src.failure_injection.loop import LoopInjector
    
    print("\n" + "="*60)
    print("✅ ALL IMPORTS SUCCESSFUL!")
    print("="*60)
    print("\nAll offline augmentation components are ready.")
    print("You can now run: python scripts/generate_offline_dataset.py")
    
except ImportError as e:
    print(f"\n❌ IMPORT ERROR: {e}")
    print("\nPlease install missing dependencies:")
    print("  pip install datasets pillow numpy scikit-image pyparsing")
    sys.exit(1)
    
except Exception as e:
    print(f"\n❌ UNEXPECTED ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
