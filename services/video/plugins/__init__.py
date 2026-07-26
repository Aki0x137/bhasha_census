"""Auto-register all default MVP plugins when this package is imported."""
from services.video.plugins.face_detector import register as _r1
from services.video.plugins.frame_quality import register as _r2
from services.video.plugins.pose_estimator import register as _r3
from services.video.plugins.face_tracker import register as _r4
from services.video.plugins.blink_detector import register as _r5
from services.video.plugins.mouth_movement_detector import register as _r6
from services.video.plugins.spoof_detector import register as _r7
from services.video.plugins.temporal_anomaly_detector import register as _r8
from services.video.plugins.doc_frame_cue import register as _r9
from services.video.plugins.kognition_liveness import register as _r10

_r1(); _r2(); _r3(); _r4(); _r5(); _r6(); _r7(); _r8(); _r9(); _r10()
