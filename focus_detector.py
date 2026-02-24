"""
Focus Detection System with Face Absence Tracking
Combines head pose estimation, eye tracking, and face presence detection
to monitor student engagement during study sessions.

FIXED VERSION: Corrected time calculation logic
- unfocus_time only counts periods AFTER exceeding 2-second threshold
- Brief look-aways (<2s) count as focus_time
- When threshold is crossed, the entire period (including initial 2s) is transferred to unfocus_time

Requirements:
    pip install opencv-python mediapipe numpy scipy
"""

import cv2 as cv
import mediapipe as mp
import numpy as np
from datetime import datetime
from scipy.spatial import distance as dist
from collections import deque

# MediaPipe initialization
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles
mp_face_mesh = mp.solutions.face_mesh


class HeadPoseEstimator:
    """
    Estimates head orientation using facial landmarks and PnP algorithm.
    Returns pitch, yaw, and roll angles in degrees.
    """
    def __init__(self):
        # 3D model points for a generic face (in millimeters)
        self.model_points = np.array([
            (0.0, 0.0, 0.0),          # Nose tip
            (0.0, -330.0, -65.0),     # Chin
            (-225.0, 170.0, -135.0),  # Left eye corner
            (225.0, 170.0, -135.0),   # Right eye corner
            (-150.0, -150.0, -125.0), # Left mouth corner
            (150.0, -150.0, -125.0)   # Right mouth corner
        ], dtype=np.float64)
        
        self.dist_coeffs = np.zeros((4, 1))
        self.pose_history = deque(maxlen=3)
    
    def estimate_pose(self, landmarks, frame_shape):
        h, w = frame_shape[:2]
        
        # Extract 2D landmark positions
        image_points = np.array([
            (landmarks[1].x * w, landmarks[1].y * h),
            (landmarks[152].x * w, landmarks[152].y * h),
            (landmarks[33].x * w, landmarks[33].y * h),
            (landmarks[263].x * w, landmarks[263].y * h),
            (landmarks[61].x * w, landmarks[61].y * h),
            (landmarks[291].x * w, landmarks[291].y * h)
        ], dtype=np.float64)
        
        # Camera matrix estimation
        focal_length = w
        center = (w / 2, h / 2)
        camera_matrix = np.array([
            [focal_length, 0, center[0]],
            [0, focal_length, center[1]],
            [0, 0, 1]
        ], dtype=np.float64)
        
        # Solve for pose using PnP
        success, rotation_vector, translation_vector = cv.solvePnP(
            self.model_points,
            image_points,
            camera_matrix,
            self.dist_coeffs,
            flags=cv.SOLVEPNP_ITERATIVE
        )
        
        if not success:
            return (0, 0, 0), None, None
        
        # Convert rotation vector to Euler angles
        rotation_matrix, _ = cv.Rodrigues(rotation_vector)
        pose_matrix = cv.hconcat((rotation_matrix, translation_vector))
        _, _, _, _, _, _, euler_angles = cv.decomposeProjectionMatrix(pose_matrix)
        
        pitch, yaw, roll = euler_angles.flatten()[:3]
        
        # Apply temporal smoothing
        self.pose_history.append((pitch, yaw, roll))
        
        if len(self.pose_history) > 0:
            avg_pitch = np.mean([p[0] for p in self.pose_history])
            avg_yaw = np.mean([p[1] for p in self.pose_history])
            avg_roll = np.mean([p[2] for p in self.pose_history])
            smoothed_pose = (avg_pitch, avg_yaw, avg_roll)
        else:
            smoothed_pose = (pitch, yaw, roll)
        
        return smoothed_pose, rotation_vector, translation_vector
    
    def draw_pose_axes(self, frame, landmarks, rotation_vector, translation_vector):
        """Draw coordinate axes on the face to visualize head orientation"""
        if rotation_vector is None or translation_vector is None:
            return
        
        h, w = frame.shape[:2]
        
        focal_length = w
        center = (w / 2, h / 2)
        camera_matrix = np.array([
            [focal_length, 0, center[0]],
            [0, focal_length, center[1]],
            [0, 0, 1]
        ], dtype=np.float64)
        
        axis_length = 150.0
        axes_points = np.array([
            (0, 0, 0),
            (axis_length, 0, 0),
            (0, axis_length, 0),
            (0, 0, axis_length)
        ], dtype=np.float64)
        
        projected_points, _ = cv.projectPoints(
            axes_points,
            rotation_vector,
            translation_vector,
            camera_matrix,
            self.dist_coeffs
        )
        
        projected_points = projected_points.reshape(-1, 2).astype(int)
        nose_tip = (int(landmarks[1].x * w), int(landmarks[1].y * h))
        
        # Draw X, Y, Z axes
        cv.line(frame, nose_tip, tuple(projected_points[1]), (0, 0, 255), 3)
        cv.line(frame, nose_tip, tuple(projected_points[2]), (0, 255, 0), 3)
        cv.line(frame, nose_tip, tuple(projected_points[3]), (255, 0, 0), 3)


class EnhancedFocusDetector:
    """
    Main class for detecting student focus and presence.
    Tracks both absence periods (when face is not detected) and 
    unfocused periods (when face is present but looking away).
    """
    def __init__(self, debug_mode=True):
        self.head_pose_estimator = HeadPoseEstimator()
        self.debug_mode = debug_mode
        
        # Head orientation thresholds in degrees
        self.PITCH_THRESHOLD = 20  # Up/down
        self.YAW_THRESHOLD = 25    # Left/right
        self.ROLL_THRESHOLD = 20   # Head tilt
        
        # Eye aspect ratio thresholds
        self.EAR_THRESHOLD = 0.21
        self.EAR_CLOSED_THRESHOLD = 0.15
        
        # Focus detection parameters
        self.focus_history = deque(maxlen=5)
        self.UNFOCUS_TIME_THRESHOLD = 2.0 # seconds
        self.unfocused_periods = []
        self.unfocused_start = None
        self.frames_unfocused = 0
        
        # Face absence tracking
        self.face_detected = True
        self.frames_without_face = 0
        self.ABSENCE_THRESHOLD_FRAMES = 5
        self.absence_start_time = None
        self.absence_periods = []
        
        # Eye blink tracking
        self.total_blinks = 0
        self.blink_counter = 0
        self.eyes_closed_frames = 0
        self.DROWSY_THRESHOLD_FRAMES = 30
        
        self.total_seconds_tracked = 0
        self.focus_time = 0
        self.unfocus_time = 0
        self.absence_time = 0
        self.frame_count = 0
        self.last_frame_time = None
        self.current_violations = []
        
        # Configurable focus zones
        self.focus_zones = {
            'strict': {'pitch': 12, 'yaw': 15, 'roll': 12},
            'normal': {'pitch': 20, 'yaw': 25, 'roll': 20},
            'relaxed': {'pitch': 30, 'yaw': 35, 'roll': 25}
        }
        self.current_zone = 'normal'
    
    def set_focus_zone(self, zone_name):
        """Update threshold values based on selected zone"""
        if zone_name in self.focus_zones:
            self.current_zone = zone_name
            zone = self.focus_zones[zone_name]
            self.PITCH_THRESHOLD = zone['pitch']
            self.YAW_THRESHOLD = zone['yaw']
            self.ROLL_THRESHOLD = zone['roll']
            print(f"Focus zone changed to: {zone_name.upper()}")
    
    def handle_face_absence(self, face_present, current_time):
        """
        Track periods when the person is completely absent from camera view.
        Updates absence_periods list with start/end times and durations.
        """
        if face_present:
            self.frames_without_face = 0
            
            # Person returned after being absent
            if not self.face_detected and self.absence_start_time is not None:
                absence_end_time = current_time
                duration = (absence_end_time - self.absence_start_time).total_seconds()
                
                self.absence_periods.append({
                    'start': self.absence_start_time,
                    'end': absence_end_time,
                    'duration': duration
                })
                
                print(f"Person returned at {absence_end_time.strftime('%H:%M:%S')} "
                      f"(absent for {duration:.1f}s)")
                
                self.absence_start_time = None
                self.face_detected = True
        else:
            self.frames_without_face += 1
            
            # Person has been absent for enough frames to confirm
            if self.frames_without_face >= self.ABSENCE_THRESHOLD_FRAMES and self.face_detected:
                self.face_detected = False
                self.absence_start_time = current_time
                print(f"Person left camera view at {current_time.strftime('%H:%M:%S')}")
                
                # Close any open unfocus period (with threshold check)
                if self.unfocused_start is not None:
                    unfocus_end = current_time
                    duration = (unfocus_end - self.unfocused_start).total_seconds()
                    
                    # Only log if it exceeded the threshold
                    if duration >= self.UNFOCUS_TIME_THRESHOLD:
                        self.unfocused_periods.append({
                            'start': self.unfocused_start,
                            'end': unfocus_end,
                            'duration': duration
                        })
                        
                        # Apply time correction
                        time_miscounted = min(duration, self.UNFOCUS_TIME_THRESHOLD)
                        self.focus_time -= time_miscounted
                        self.unfocus_time += time_miscounted
                        
                        print(f"[{self.current_zone}] Unfocus Event (before absence): {duration:.1f}s")
                    # else: brief look-away (<2s) - stays as focus_time
                    
                    self.unfocused_start = None
            
            if not self.face_detected:
                # Use actual time delta if possible, else estimate
                if hasattr(self, 'last_frame_time') and self.last_frame_time:
                    dt = (current_time - self.last_frame_time).total_seconds()
                else:
                    dt = 0.033
                self.absence_time += dt
    
    def calculate_ear(self, eye_landmarks_indices, landmarks, frame_shape):
        """
        Calculate Eye Aspect Ratio (EAR) for blink and drowsiness detection.
        Lower values indicate closed or partially closed eyes.
        """
        h, w = frame_shape[:2]
        points = [(landmarks[i].x * w, landmarks[i].y * h) 
                  for i in eye_landmarks_indices]
        
        # Vertical eye distances
        A = dist.euclidean(points[1], points[5])
        B = dist.euclidean(points[2], points[4])
        
        # Horizontal eye distance
        C = dist.euclidean(points[0], points[3])
        
        ear = (A + B) / (2.0 * C) if C > 0 else 0
        return ear
    
    def calculate_head_alignment_score(self, pitch, yaw, roll):
        """
        Score how well aligned the head is with the camera/screen.
        Returns 0.0 (very misaligned) to 1.0 (perfectly aligned).
        Also populates current_violations list with specific issues.
        """
        self.current_violations = []
        
        # Check each angle against threshold
        if abs(pitch) > self.PITCH_THRESHOLD:
            direction = "UP" if pitch < 0 else "DOWN"
            self.current_violations.append(f"Looking {direction} ({abs(pitch):.1f} deg)")
        
        if abs(yaw) > self.YAW_THRESHOLD:
            direction = "LEFT" if yaw < 0 else "RIGHT"
            self.current_violations.append(f"Looking {direction} ({abs(yaw):.1f} deg)")
        
        if abs(roll) > self.ROLL_THRESHOLD:
            direction = "LEFT" if roll < 0 else "RIGHT"
            self.current_violations.append(f"Head tilted {direction} ({abs(roll):.1f} deg)")
        
        # Calculate normalized deviations
        pitch_dev = min(abs(pitch) / self.PITCH_THRESHOLD, 1.5)
        yaw_dev = min(abs(yaw) / self.YAW_THRESHOLD, 1.5)
        roll_dev = min(abs(roll) / self.ROLL_THRESHOLD, 1.5)
        
        # Weighted combination - yaw is most important for screen viewing
        score = (
            0.3 * max(0, 1 - pitch_dev) +
            0.5 * max(0, 1 - yaw_dev) +
            0.2 * max(0, 1 - roll_dev)
        )
        
        return score
    
    def calculate_eye_state_score(self, left_ear, right_ear):
        """
        Score eye openness state.
        Returns 0.0 (closed/drowsy) to 1.0 (wide open).
        """
        avg_ear = (left_ear + right_ear) / 2
        
        if avg_ear < self.EAR_CLOSED_THRESHOLD:
            return 0.0
        elif avg_ear < self.EAR_THRESHOLD:
            ratio = (avg_ear - self.EAR_CLOSED_THRESHOLD) / (self.EAR_THRESHOLD - self.EAR_CLOSED_THRESHOLD)
            return 0.5 * ratio
        else:
            return min(1.0, 0.5 + 0.5 * (avg_ear - self.EAR_THRESHOLD) / 0.1)
    
    def detect_blink(self, left_ear, right_ear):
        """Track blinks and detect drowsiness from prolonged eye closure"""
        avg_ear = (left_ear + right_ear) / 2
        
        if avg_ear < self.EAR_THRESHOLD:
            self.blink_counter += 1
            if avg_ear < self.EAR_CLOSED_THRESHOLD:
                self.eyes_closed_frames += 1
        else:
            if self.blink_counter >= 2:
                self.total_blinks += 1
            self.blink_counter = 0
            self.eyes_closed_frames = 0
        
        is_drowsy = self.eyes_closed_frames > self.DROWSY_THRESHOLD_FRAMES
        return is_drowsy
    
    def calculate_focus_score(self, head_pose, left_ear, right_ear):
        """
        Calculate overall focus score combining head pose and eye state.
        Returns score (0-1) and component breakdown dictionary.
        """
        pitch, yaw, roll = head_pose
        
        head_score = self.calculate_head_alignment_score(pitch, yaw, roll)
        eye_score = self.calculate_eye_state_score(left_ear, right_ear)
        is_drowsy = self.detect_blink(left_ear, right_ear)
        
        if is_drowsy:
            eye_score *= 0.2
        
        # Weighted combination: head alignment is more important
        total_score = 0.6 * head_score + 0.4 * eye_score
        
        components = {
            'head_score': head_score,
            'eye_score': eye_score,
            'is_drowsy': is_drowsy,
            'angles': {'pitch': pitch, 'yaw': yaw, 'roll': roll},
            'ear': {'left': left_ear, 'right': right_ear},
            'violations': self.current_violations.copy()
        }
        
        return total_score, components
    
    def update_focus_state(self, focus_score, current_time):
        """
        Update focus state with temporal smoothing to avoid false positives.
        Requires sustained unfocus before logging an unfocus period.
        
        FIXED TIME TRACKING LOGIC:
        - Only periods exceeding UNFOCUS_TIME_THRESHOLD (2s) count as unfocus_time
        - Brief look-aways (<2s) are counted as focus_time
        - When threshold is crossed, the ENTIRE duration (including initial 2s) is transferred to unfocus_time
        """
        self.focus_history.append(focus_score)
        
        # Use median for smoothing
        if len(self.focus_history) >= 3:
            smoothed_score = np.median(list(self.focus_history))
        else:
            smoothed_score = focus_score
        
        is_focused = smoothed_score >= 0.5
        
        # 1. Calculate time delta since last frame for accurate non-linear tracking
        if self.last_frame_time is None:
            dt = 0.033  # Default to ~30fps for the first frame
        else:
            dt = (current_time - self.last_frame_time).total_seconds()
        self.last_frame_time = current_time
        self.total_seconds_tracked += dt

        # 2. Handle focus state transitions and time accumulation
        if not is_focused:
            # Person is currently unfocused
            self.frames_unfocused += 1
            
            if self.unfocused_start is None:
                # Just started being unfocused
                self.unfocused_start = current_time
                # Initial unfocused frame still counts as focus time (not yet confirmed unfocus)
                self.focus_time += dt
            else:
                # Continue being unfocused - check if we've crossed the threshold
                elapsed_away = (current_time - self.unfocused_start).total_seconds()
                
                if elapsed_away >= self.UNFOCUS_TIME_THRESHOLD:
                    # Confirmed sustained unfocus - count as unfocus time
                    self.unfocus_time += dt
                else:
                    # Still under threshold - keep counting as focus time
                    self.focus_time += dt
        else:
            # Person is currently focused
            if self.unfocused_start is not None:
                # Person WAS unfocused but refocused now
                duration = (current_time - self.unfocused_start).total_seconds()
                
                # Log event only if it exceeded the threshold
                if duration >= self.UNFOCUS_TIME_THRESHOLD:
                    self.unfocused_periods.append({
                        'start': self.unfocused_start,
                        'end': current_time,
                        'duration': duration
                    })
                    print(f"[{self.current_zone}] Unfocus Event: {duration:.1f}s")
                    
                    # CRITICAL FIX: Now we need to ADJUST the time counters
                    # We've been counting this as focus_time up to the threshold
                    # Now we need to move the ENTIRE duration to unfocus_time
                    time_miscounted = min(duration, self.UNFOCUS_TIME_THRESHOLD)
                    self.focus_time -= time_miscounted  # Remove what we incorrectly added
                    self.unfocus_time += time_miscounted  # Add it to unfocus
                # else: brief look-away (<2s) - stays as focus_time, no adjustment needed
                
                self.unfocused_start = None
            
            self.frames_unfocused = 0
            # Currently focused, add to focus time
            self.focus_time += dt
        
        self.frame_count += 1
        return is_focused, smoothed_score
    
    def draw_debug_overlay(self, frame, components, focus_score, is_focused):
        """Display real-time debug information on frame"""
        h, w = frame.shape[:2]
        
        # Semi-transparent overlay panel
        overlay = frame.copy()
        panel_height = 340
        cv.rectangle(overlay, (0, 0), (450, panel_height), (0, 0, 0), -1)
        cv.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
        
        y_offset = 25
        line_height = 25
        
        # Title
        cv.putText(frame, "FOCUS & ABSENCE DETECTION", (10, y_offset),
                  cv.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        y_offset += line_height + 5
        
        # Face presence status
        if self.face_detected:
            presence_text = "PRESENT"
            presence_color = (0, 255, 0)
        else:
            presence_text = "ABSENT"
            presence_color = (0, 0, 255)
        
        cv.putText(frame, f"Face: {presence_text}", (10, y_offset),
                  cv.FONT_HERSHEY_SIMPLEX, 0.6, presence_color, 2)
        y_offset += line_height
        
        if not self.face_detected:
            # Show absence duration
            if self.absence_start_time:
                absence_duration = (datetime.now() - self.absence_start_time).total_seconds()
                cv.putText(frame, f"Absent for: {absence_duration:.1f}s", (10, y_offset),
                          cv.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 1)
                y_offset += line_height
        else:
            # Focus status
            status_text = "FOCUSED" if is_focused else "UNFOCUSED"
            status_color = (0, 255, 0) if is_focused else (0, 0, 255)
            cv.putText(frame, f"Status: {status_text}", (10, y_offset),
                      cv.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)
            y_offset += line_height
            
            # Focus score progress bar
            cv.putText(frame, f"Focus Score: {focus_score:.2f}", (10, y_offset),
                      cv.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            bar_width = int(300 * focus_score)
            bar_color = (0, int(255 * focus_score), int(255 * (1 - focus_score)))
            cv.rectangle(frame, (10, y_offset + 5), (310, y_offset + 20), (50, 50, 50), -1)
            cv.rectangle(frame, (10, y_offset + 5), (10 + bar_width, y_offset + 20), bar_color, -1)
            threshold_x = int(10 + 300 * 0.5)
            cv.line(frame, (threshold_x, y_offset + 5), (threshold_x, y_offset + 20), (255, 255, 255), 2)
            y_offset += 30
            
            # Head pose angles
            angles = components['angles']
            cv.putText(frame, "Head Pose:", (10, y_offset),
                      cv.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            y_offset += line_height
            
            # Display each angle with status indicator
            for angle_name, angle_val, threshold in [
                ('Pitch', angles['pitch'], self.PITCH_THRESHOLD),
                ('Yaw', angles['yaw'], self.YAW_THRESHOLD),
                ('Roll', angles['roll'], self.ROLL_THRESHOLD)
            ]:
                status = "OK" if abs(angle_val) < threshold else "X"
                color = (0, 255, 0) if abs(angle_val) < threshold else (0, 0, 255)
                cv.putText(frame, f"  [{status}] {angle_name}: {angle_val:6.1f} deg (limit {threshold})",
                          (10, y_offset), cv.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)
                y_offset += line_height - 5
            
            # Current violations
            if components['violations']:
                y_offset += 5
                cv.putText(frame, "Violations:", (10, y_offset),
                          cv.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 1)
                y_offset += line_height - 5
                for violation in components['violations']:
                    cv.putText(frame, f"  {violation}", (10, y_offset),
                              cv.FONT_HERSHEY_SIMPLEX, 0.4, (0, 165, 255), 1)
                    y_offset += line_height - 8
        
        # Session statistics
        y_offset = max(y_offset, panel_height - 60)
        if self.total_seconds_tracked > 0:
            focus_percentage = (self.focus_time / self.total_seconds_tracked) * 100
        else:
            focus_percentage = 0
        cv.putText(frame, f"Focus: {focus_percentage:.1f}%", (10, y_offset),
                  cv.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)
        y_offset += line_height - 5
        cv.putText(frame, f"Blinks: {self.total_blinks}", (10, y_offset),
                  cv.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)
    
    def finalize_session(self):
        """Close any open tracking periods at end of session"""
        current_time = datetime.now()
        
        # Close open absence period
        if not self.face_detected and self.absence_start_time is not None:
            duration = (current_time - self.absence_start_time).total_seconds()
            self.absence_periods.append({
                'start': self.absence_start_time,
                'end': current_time,
                'duration': duration
            })
        
        # Close open unfocus period
        if self.unfocused_start is not None:
            duration = (current_time - self.unfocused_start).total_seconds()
            if duration >= self.UNFOCUS_TIME_THRESHOLD:
                self.unfocused_periods.append({
                    'start': self.unfocused_start,
                    'end': current_time,
                    'duration': duration
                })
                # Adjust time counters
                time_miscounted = min(duration, self.UNFOCUS_TIME_THRESHOLD)
                self.focus_time -= time_miscounted
                self.unfocus_time += time_miscounted
    
    def get_report(self):
        """Generate comprehensive session report with all statistics"""
        if self.frame_count == 0:
            return None
        
        total_time = self.total_seconds_tracked
        focus_percentage = (self.focus_time / max(total_time, 0.1)) * 100
        absence_percentage = (self.absence_time / max(total_time, 0.1)) * 100
        
        report = {
            'total_time': total_time,
            'focus_time': self.focus_time,
            'unfocus_time': self.unfocus_time,
            'absence_time': self.absence_time,
            'focus_percentage': focus_percentage,
            'absence_percentage': absence_percentage,
            'total_blinks': self.total_blinks,
            'unfocus_events': len(self.unfocused_periods),
            'absence_events': len(self.absence_periods),
            'unfocused_periods': self.unfocused_periods,
            'absence_periods': self.absence_periods,
            'current_zone': self.current_zone
        }
        
        if len(self.unfocused_periods) > 0:
            report['average_unfocus_duration'] = np.mean(
                [p['duration'] for p in self.unfocused_periods]
            )
            report['longest_unfocus'] = max(
                [p['duration'] for p in self.unfocused_periods]
            )
        
        if len(self.absence_periods) > 0:
            report['average_absence_duration'] = np.mean(
                [p['duration'] for p in self.absence_periods]
            )
            report['longest_absence'] = max(
                [p['duration'] for p in self.absence_periods]
            )
        
        return report


def main():
    """Main application loop"""
    # Initialize camera
    cap = cv.VideoCapture(0)
    
    cap.set(cv.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv.CAP_PROP_FRAME_HEIGHT, 720)
    cap.set(cv.CAP_PROP_FPS, 30)
    
    focus_detector = EnhancedFocusDetector(debug_mode=True)
    focus_detector.set_focus_zone('normal')
    
    print("\n" + "="*70)
    print("FOCUS AND ABSENCE DETECTION SYSTEM - FIXED VERSION")
    print("="*70)
    print("\nFeatures:")
    print("  - Tracks complete absence periods (when person leaves camera)")
    print("  - Tracks unfocus periods (when present but not paying attention)")
    print("  - FIXED: Accurate time calculation for focus/unfocus")
    print("  - Only periods >2s count as unfocus_time")
    print("  - Generates comprehensive session report")
    print("\nControls:")
    print("  1 - Strict mode (tight thresholds)")
    print("  2 - Normal mode (recommended)")
    print("  3 - Relaxed mode (loose thresholds)")
    print("  D - Toggle debug overlay")
    print("  Q - Quit and show report")
    print("="*70 + "\n")
    
    with mp_face_mesh.FaceMesh(
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    ) as face_mesh:
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            frame = cv.flip(frame, 1)
            rgb = cv.cvtColor(frame, cv.COLOR_BGR2RGB)
            result = face_mesh.process(rgb)
            current_time = datetime.now()
            
            # Update face presence state
            face_present = result.multi_face_landmarks is not None
            focus_detector.handle_face_absence(face_present, current_time)
            
            if result.multi_face_landmarks:
                landmarks = result.multi_face_landmarks[0].landmark
                
                # Estimate head pose
                head_pose, rotation_vec, translation_vec = \
                    focus_detector.head_pose_estimator.estimate_pose(landmarks, frame.shape)
                
                # Calculate eye aspect ratios
                left_eye_indices = [33, 160, 158, 133, 153, 144]
                right_eye_indices = [362, 385, 387, 263, 373, 380]
                
                left_ear = focus_detector.calculate_ear(left_eye_indices, landmarks, frame.shape)
                right_ear = focus_detector.calculate_ear(right_eye_indices, landmarks, frame.shape)
                
                # Calculate focus score
                focus_score, components = focus_detector.calculate_focus_score(
                    head_pose, left_ear, right_ear
                )
                
                # Update focus state
                is_focused, smoothed_score = focus_detector.update_focus_state(
                    focus_score, current_time
                )
                
                # Draw face mesh
                mp_drawing.draw_landmarks(
                    image=frame,
                    landmark_list=result.multi_face_landmarks[0],
                    connections=mp_face_mesh.FACEMESH_TESSELATION,
                    landmark_drawing_spec=None,
                    connection_drawing_spec=mp_drawing_styles.get_default_face_mesh_tesselation_style()
                )
                
                # Draw pose axes
                focus_detector.head_pose_estimator.draw_pose_axes(
                    frame, landmarks, rotation_vec, translation_vec
                )
                
                # Draw debug overlay
                if focus_detector.debug_mode:
                    focus_detector.draw_debug_overlay(
                        frame, components, smoothed_score, is_focused
                    )
            else:
                # No face detected
                if focus_detector.debug_mode:
                    components = {
                        'head_score': 0,
                        'eye_score': 0,
                        'is_drowsy': False,
                        'angles': {'pitch': 0, 'yaw': 0, 'roll': 0},
                        'ear': {'left': 0, 'right': 0},
                        'violations': []
                    }
                    focus_detector.draw_debug_overlay(frame, components, 0, False)
                
                cv.putText(frame, "No face detected", (50, 50),
                          cv.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            
            # Display frame
            cv.imshow('Focus Detection System', frame)
            
            # Handle keyboard input
            key = cv.waitKey(1) & 0xFF
            
            if key == ord('q'):
                focus_detector.finalize_session()
                break
            elif key == ord('1'):
                focus_detector.set_focus_zone('strict')
            elif key == ord('2'):
                focus_detector.set_focus_zone('normal')
            elif key == ord('3'):
                focus_detector.set_focus_zone('relaxed')
            elif key == ord('d'):
                focus_detector.debug_mode = not focus_detector.debug_mode
                status = "ON" if focus_detector.debug_mode else "OFF"
                print(f"Debug mode: {status}")
    
    # Cleanup
    cap.release()
    cv.destroyAllWindows()
    
    # Generate session report
    print("\n" + "="*80)
    print("SESSION REPORT")
    print("="*80)
    
    report = focus_detector.get_report()
    
    if report:
        print(f"\nSession Statistics:")
        print(f"   Total time: {report['total_time']:.1f} seconds ({report['total_time']/60:.1f} minutes)")
        print(f"   Focus time: {report['focus_time']:.1f} seconds ({report['focus_percentage']:.1f}%)")
        print(f"   Unfocus time: {report['unfocus_time']:.1f} seconds")
        print(f"   Absence time: {report['absence_time']:.1f} seconds ({report['absence_percentage']:.1f}%)")
        print(f"   Total blinks: {report['total_blinks']}")
        
        print(f"\nAbsence Periods: {report['absence_events']}")
        if report['absence_events'] > 0:
            print(f"   Average duration: {report['average_absence_duration']:.1f} seconds")
            print(f"   Longest absence: {report['longest_absence']:.1f} seconds")
            
            print("\nDetailed Absence Periods:")
            for i, period in enumerate(report['absence_periods'], 1):
                print(f"   {i}. {period['start'].strftime('%H:%M:%S')} to "
                      f"{period['end'].strftime('%H:%M:%S')} ({period['duration']:.1f}s)")
        
        print(f"\nUnfocus Periods (while present): {report['unfocus_events']}")
        if report['unfocus_events'] > 0:
            print(f"   Average duration: {report['average_unfocus_duration']:.1f} seconds")
            print(f"   Longest unfocus: {report['longest_unfocus']:.1f} seconds")
            
            print("\nDetailed Unfocus Periods:")
            for i, period in enumerate(report['unfocused_periods'], 1):
                print(f"   {i}. {period['start'].strftime('%H:%M:%S')} to "
                      f"{period['end'].strftime('%H:%M:%S')} ({period['duration']:.1f}s)")
        
        # Calculate effective focus rate (excluding absence time)
        present_time = report['total_time'] - report['absence_time']
        if present_time > 0:
            effective_focus = (report['focus_time'] / present_time) * 100
        else:
            effective_focus = 0
        
        print(f"\nPerformance Metrics:")
        print(f"   Focus rate while present: {effective_focus:.1f}%")
        
        if effective_focus >= 85:
            rating = "Excellent"
        elif effective_focus >= 70:
            rating = "Good"
        elif effective_focus >= 50:
            rating = "Fair"
        else:
            rating = "Poor"
        
        print(f"   Overall rating: {rating}")
        
        if report['absence_percentage'] > 20:
            print(f"\nWarning: High absence rate ({report['absence_percentage']:.1f}%)")
        
    print("="*80 + "\n")


if __name__ == "__main__":
    main()