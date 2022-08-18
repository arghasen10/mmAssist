import argparse
from datetime import datetime, timedelta
import cv2
import mediapipe as mp
import numpy as np
import time


class VideoAnnotation:
    def __init__(self, min_detection_confidence=0.5, min_tracking_confidence=0.5, thickness=1, circle_radius=1,
                 y_min=-5, y_max=8, x_min=-7, x_max=7):
        self.thickness = thickness
        self.min_tracking_confidence = min_tracking_confidence
        self.min_detection_confidence = min_detection_confidence
        self.circle_radius = circle_radius
        self.file_name = ''

        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(min_detection_confidence=0.5, min_tracking_confidence=0.5)

        self.mp_drawing = mp.solutions.drawing_utils

        self.drawing_spec = self.mp_drawing.DrawingSpec(thickness=1, circle_radius=1)
        self.y_min = y_min
        self.y_max = y_max
        self.x_min = x_min
        self.x_max = x_max

    def process(self, file_name):
        cap = cv2.VideoCapture(file_name)
        fps = cap.get(cv2.CAP_PROP_FPS)
        starttime = datetime.strptime(file_name.split('/')[-1].split('.')[0], "%Y%m%d_%H%M%S")
        frame_count = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if ret is True:
                frame_count += 1
                seconds = round(frame_count / fps)
                video_time = starttime + timedelta(seconds=seconds)
                start = time.time()
                image = cv2.cvtColor(cv2.flip(frame, 1), cv2.COLOR_BGR2RGB)
                image.flags.writeable = False
                results = self.face_mesh.process(image)
                image.flags.writeable = True
                image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                img_h, img_w, img_c = image.shape

                face_3d = []
                face_2d = []

                if results.multi_face_landmarks:
                    for face_landmarks in results.multi_face_landmarks:
                        for idX, lm in enumerate(face_landmarks.landmark):
                            if idX == 33 or idX == 263 or idX == 1 or idX == 61 or idX == 291 or idX == 199:
                                if idX == 1:
                                    nose_2d = (lm.x * img_w, lm.y * img_h)
                                    nose_3d = (lm.x * img_w, lm.y * img_h, lm.z * 3000)
                                x, y = int(lm.x * img_w), int(lm.y * img_h)
                                face_2d.append([x, y])
                                face_3d.append([x, y, lm.z])

                        face_2d = np.array(face_2d, dtype=np.float64)
                        face_3d = np.array(face_3d, dtype=np.float64)

                        focal_length = 1 * img_w

                        cam_matrix = np.array([[focal_length, 0, img_h / 2],
                                               [0, focal_length, img_w / 2],
                                               [0, 0, 1]])

                        dist_matrix = np.zeros((4, 1), dtype=np.float64)

                        success, rot_vec, trans_vec = cv2.solvePnP(face_3d, face_2d, cam_matrix, dist_matrix)

                        rmat, jac = cv2.Rodrigues(rot_vec)

                        angles, mtxR, mtxQ, Qx, Qy, Qz = cv2.RQDecomp3x3(rmat)

                        x = angles[0] * 360
                        y = angles[1] * 360
                        z = angles[2] * 360

                        if y < self.y_min:
                            text = "looking left"
                        elif y > self.y_max:
                            text = "looking right"
                        elif x < self.x_min:
                            text = "looking down"
                        elif x > self.x_max:
                            text = "looking up"
                        else:
                            text = "forward"

                        # datetime_object = datetime.datetime.now()

                        nose_3d_projection, jacobian = cv2.projectPoints(nose_3d, rot_vec, trans_vec, cam_matrix,
                                                                         dist_matrix)

                        p1 = (int(nose_2d[0]), int(nose_2d[1]))
                        p2 = (int(nose_2d[0] + y * 10), int(nose_2d[1] - x * 10))

                        cv2.line(image, p1, p2, (255, 0, 0), 3)

                        cv2.putText(image, text, (20, 50), cv2.FONT_HERSHEY_COMPLEX, 2, (0, 255, 0), 2)
                        cv2.putText(image, 'x: ' + str(np.round(x, 2)), (500, 50), cv2.FONT_HERSHEY_SIMPLEX, 1,
                                    (0, 0, 255), 2)
                        cv2.putText(image, 'y: ' + str(np.round(y, 2)), (500, 100), cv2.FONT_HERSHEY_SIMPLEX, 1,
                                    (0, 0, 255), 2)
                        cv2.putText(image, 'z: ' + str(np.round(z, 2)), (500, 150), cv2.FONT_HERSHEY_SIMPLEX, 1,
                                    (0, 0, 255), 2)

                    end = time.time()
                    totaltime = end - start

                    fps = 1 / totaltime
                    # print("FPS: ", fps)
                    cv2.putText(image, str(video_time), (20, 450), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 1, 2)
                    # cv2.putText(image, f'FPS: {int(fps)}', (20, 450), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 2)

                    self.mp_drawing.draw_landmarks(
                        image=image,
                        landmark_list=face_landmarks,
                        connections=self.mp_face_mesh.FACEMESH_CONTOURS,
                        landmark_drawing_spec=self.drawing_spec,
                        connection_drawing_spec=self.drawing_spec)

                cv2.imshow("Image", image)

                if cv2.waitKey(1) & 0xFF == ord('s'):
                    break
            else:
                break

        cap.release()
        cv2.destroyAllWindows()


def parseArg():
    parser = argparse.ArgumentParser(description='Run Experiment')
    parser.add_argument('--user', help='Select user running the vehicle', default="anirban",
                        choices=["anirban", "sugandh"])
    parser.add_argument('--ext', help='Extension of the video file', default=".mp4",
                        choices=[".mp4", ".avi"])
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    args = parseArg()
    video_annotator = VideoAnnotation()
    file_name = args.user + args.ext
    video_annotator.process(file_name=file_name)
