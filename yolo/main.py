from ultralytics import YOLO, checks
import cv2
import supervision as sv

def predictions(image):
  '''Метод принимает image (cv2 формат), 
  а возвращает список свободных мест, и размеченное изображение'''  
  model = YOLO('parking_model.pt') 
  tracker = sv.ByteTrack() 
  
  results = model(image)[0]
  detections = sv.Detections.from_ultralytics(results)
  detections = tracker.update_with_detections(detections)

  bounding_box_annotator = sv.BoundingBoxAnnotator(thickness=1, color = sv.ColorPalette.from_hex(['#008000','#ff0000']))
  label_annotator = sv.LabelAnnotator(text_scale=0.5, color=sv.ColorPalette.from_hex(['#008000','#ff0000']))

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
    if class_id == 0
  ]

  return freePlace, annotated_image
