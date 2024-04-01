from ultralytics import YOLO, checks
import cv2
import numpy as np
import supervision as sv



def predictions(image):

  '''Метод принимает image, 
  а возвращает список свободных мест, и размеченное изображение'''

  model = YOLO('../yolo/best.pt')
  tracker = sv.ByteTrack()




  #image = cv2.imread(image)
  #print(image)
  results = model(image)[0]

  detections = sv.Detections.from_ultralytics(results)
  detections = tracker.update_with_detections(detections)
  #print(detections.tracker_id)

  bounding_box_annotator = sv.BoundingBoxAnnotator(thickness=1, color = sv.ColorPalette.from_hex(['#0000ff','#008000']))
  label_annotator = sv.LabelAnnotator(text_scale=0.5, color=sv.ColorPalette.from_hex(['#0000ff','#008000']))

  labels = [
      f"#{tracker_id}"
      for tracker_id
      in detections.tracker_id
  ]

  annotated_image = bounding_box_annotator.annotate(scene=image, detections=detections)
  annotated_image = label_annotator.annotate(scene=annotated_image, detections=detections, labels=labels)
  freePlace = [
    f"Место №{tracker_id}" 
    for class_id, tracker_id 
    in zip(detections.class_id, detections.tracker_id) 
    if class_id == 1
  ]

  tracker.reset()
  return freePlace, annotated_image
#predictions('./test_photo/test2.jpg')
