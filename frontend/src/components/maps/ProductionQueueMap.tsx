import { useEffect, useRef, useState } from "react";
import Map from "ol/Map";
import View from "ol/View";
import TileLayer from "ol/layer/Tile";
import VectorLayer from "ol/layer/Vector";
import VectorSource from "ol/source/Vector";
import { OSM } from "ol/source";
import { fromLonLat } from "ol/proj";
import Feature from "ol/Feature";
import Point from "ol/geom/Point";
import { Style, Circle, Fill, Stroke } from "ol/style";
import "ol/ol.css";
import { Overlay } from "ol";
import { ProductionQueueItem } from "@/store/services/dashboardApi";

interface ProductionQueueMapProps {
  data: ProductionQueueItem[] | undefined;
  setIsGeocodingLoading?: (isGeocodingLoading: boolean) => void;
}

// Add this new function before the ProductionQueueMap component
async function getCoordinates(
  location: string
): Promise<[number, number] | null> {
  try {
    const response = await fetch(
      `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(
        location
      )}`
    );
    const data = await response.json();

    if (data && data[0]) {
      return [parseFloat(data[0].lon), parseFloat(data[0].lat)];
    }
    return null;
  } catch (error) {
    console.error("Error fetching coordinates:", error);
    return null;
  }
}

const ProductionQueueMap = ({
  data,
  setIsGeocodingLoading = () => {},
}: ProductionQueueMapProps) => {
  const mapRef = useRef<HTMLDivElement>(null);
  const [map, setMap] = useState<Map | null>(null);
  const [selectedItem, setSelectedItem] = useState<ProductionQueueItem | null>(
    null
  );
  const popupRef = useRef<HTMLDivElement>(null);
  const [popupVisible, setPopupVisible] = useState(false);

  useEffect(() => {
    if (!mapRef.current || !popupRef.current) return;

    const vectorSource = new VectorSource();
    const vectorLayer = new VectorLayer({
      source: vectorSource,
    });

    // Create popup overlay
    const popup = new Overlay({
      element: popupRef.current,
      positioning: "bottom-center",
      offset: [0, -10],
      stopEvent: false,
    });

    const initialMap = new Map({
      target: mapRef.current,
      layers: [
        new TileLayer({
          source: new OSM(),
        }),
        vectorLayer,
      ],
      view: new View({
        center: fromLonLat([-98.5795, 39.8283]), // Center of US
        zoom: 4,
      }),
    });

    initialMap.addOverlay(popup);

    // Handle click events
    initialMap.on("click", (event) => {
      const features = initialMap.getFeaturesAtPixel(event.pixel);
      if (features && features.length > 0) {
        const feature = features[0];
        const itemData = feature.get("data");
        const coordinates = (feature.getGeometry() as Point).getCoordinates();

        setSelectedItem(itemData);
        setPopupVisible(true);
        popup.setPosition(coordinates);
      } else {
        setPopupVisible(false);
        popup.setPosition(undefined);
      }
    });

    // Add pointer cursor on hover
    initialMap.on("pointermove", (event) => {
      const pixel = initialMap.getEventPixel(event.originalEvent);
      const hasFeature = initialMap.hasFeatureAtPixel(pixel);
      if (
        initialMap.getTarget() &&
        typeof initialMap.getTarget() === "object"
      ) {
        (initialMap.getTarget() as HTMLElement).style.cursor = hasFeature
          ? "pointer"
          : "";
      }
    });

    setMap(initialMap);

    return () => {
      initialMap.setTarget(undefined);
    };
  }, []);

  useEffect(() => {
    if (!map || !data) return;

    const vectorSource = (
      map.getLayers().getArray()[1] as VectorLayer<VectorSource>
    ).getSource();
    vectorSource?.clear();

    // Process all locations
    const addMarkers = async () => {
      setIsGeocodingLoading(true);
      try {
        for (const item of data) {
          if (!item.delivery_location) continue;

          const coords = await getCoordinates(item.delivery_location);
          if (!coords) {
            console.warn(
              `No coordinates found for location: ${item.delivery_location}`
            );
            continue;
          }

          const feature = new Feature({
            geometry: new Point(fromLonLat(coords)),
            data: item,
          });

          feature.setStyle(
            new Style({
              image: new Circle({
                radius: 8,
                fill: new Fill({
                  color: "#FF4444",
                }),
                stroke: new Stroke({
                  color: "#FFFFFF",
                  width: 2,
                }),
              }),
            })
          );

          vectorSource?.addFeature(feature);
        }

        // Fit view after all markers are added
        const features = vectorSource?.getFeatures() || [];
        if (features.length > 0) {
          const extent = vectorSource?.getExtent();
          if (extent) {
            map.getView().fit(extent, {
              padding: [50, 50, 50, 50],
              maxZoom: 6,
            });
          }
        }
      } finally {
        setIsGeocodingLoading(false);
      }
    };

    addMarkers();
  }, [map, data]);

  return (
    <div className="relative w-full h-[400px] rounded-lg overflow-hidden">
      <div
        ref={mapRef}
        className="w-full h-full"
        style={{ width: "100%", height: "400px" }}
      />
      <div
        ref={popupRef}
        className={`absolute bg-white dark:bg-gray-800 p-4 rounded-lg shadow-lg transform -translate-x-1/2 ${
          popupVisible ? "block" : "hidden"
        }`}
      >
        {selectedItem && (
          <div className="space-y-2 min-w-[300px]">
            <h3 className="font-bold text-sm">{selectedItem.customer}</h3>
            <div className="text-xs space-y-1">
              <p>
                <span className="font-medium">Order ID:</span>{" "}
                {selectedItem.order_id}
              </p>
              <p>
                <span className="font-medium">Location:</span>{" "}
                {selectedItem.delivery_location}
              </p>
              <p>
                <span className="font-medium">Quantity:</span>{" "}
                {selectedItem.quantity}
              </p>
              <p>
                <span className="font-medium">Status:</span>{" "}
                {selectedItem.status}
              </p>
              <p>
                <span className="font-medium">Delivery:</span>{" "}
                {new Date(selectedItem.delivery_date).toLocaleDateString()}
              </p>
              {selectedItem.issues && (
                <p className="text-red-500">
                  <span className="font-medium">Issues:</span>{" "}
                  {selectedItem.issues}
                </p>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ProductionQueueMap;
