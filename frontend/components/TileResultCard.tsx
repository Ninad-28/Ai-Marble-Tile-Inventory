interface TileResult {
  tile_id: number;
  sku: string;
  name: string;
  confidence: number;
  location: {
    warehouse?: string;
    aisle: string | null;
    rack: string | null;
    bin: string | null;
    display?: string;
  };
  stock: { quantity: number | null; unit: string; is_low: boolean };
  image_url: string;
  details?: {
    material?: { name: string };
    finish?: { name: string };
    style?: { name: string };
    width_cm?: number;
    height_cm?: number;
    thickness_cm?: number;
    price_per_sqm?: number;
  };
}

export default function TileResultCard({
  result,
  rank,
}: {
  result: TileResult;
  rank: number;
}) {
  const confidenceColor =
    result.confidence >= 85
      ? "text-green-600 bg-green-50"
      : result.confidence >= 70
      ? "text-yellow-600 bg-yellow-50"
      : "text-red-600 bg-red-50";

  const imageUrl = result.image_url
    ? `http://localhost:8000${result.image_url}`
    : null;

  return (
    <div
      className={`bg-white/95 backdrop-blur-sm rounded-2xl border p-5 shadow-md transition-all duration-300 transform hover:-translate-y-1 hover:shadow-2xl ${
        rank === 0
          ? "border-emerald-500 ring-2 ring-emerald-400/50"
          : "border-stone-200"
      }`}
    >
      {/* Header Row */}
      <div className="flex gap-4 items-start">

        {/* Tile Image */}
        <div className="w-24 h-24 rounded-lg overflow-hidden
                        bg-stone-100 flex-shrink-0 border border-stone-200 shadow-inner transition-all duration-300 hover:scale-105 hover:shadow-xl">
          {imageUrl ? (
            <img
              src={imageUrl}
              alt={result.name}
              className="w-full h-full object-cover transition-all duration-300 ease-out hover:scale-110"
              onError={(e) => {
                (e.target as HTMLImageElement).src =
                  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg'" +
                  " width='96' height='96'%3E%3Crect width='96' height='96'" +
                  " fill='%23e7e5e4'/%3E%3Ctext x='50%25' y='50%25'" +
                  " dominant-baseline='middle' text-anchor='middle'" +
                  " font-size='24'%3E🪨%3C/text%3E%3C/svg%3E";
              }}
            />
          ) : (
            <div className="w-full h-full flex items-center
                            justify-center text-3xl text-stone-400">
              🪨
            </div>
          )}
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between mb-1">
            <div>
              {rank === 0 && (
                <span className="text-xs font-bold bg-gradient-to-r from-emerald-500 to-cyan-500 text-white
                                 px-2 py-0.5 rounded-full mb-1 inline-block shadow">
                  Best Match
                </span>
              )}
              <p className="font-bold text-stone-800 leading-tight tracking-tight text-lg">
                {result.name}
              </p>
              <p className="text-stone-400 text-xs">{result.sku}</p>
            </div>
            <span
              className={`text-sm font-bold px-3 py-1 rounded-full
                          flex-shrink-0 ml-2 ${confidenceColor}`}
            >
              {result.confidence}% similarity
            </span>
          </div>

          <div className="flex flex-wrap gap-x-3 gap-y-1 mt-3 text-xs text-stone-500">
            {result.details?.material?.name && <span>{result.details.material.name}</span>}
            {result.details?.finish?.name && <span>Finish: {result.details.finish.name}</span>}
            {result.details?.style?.name && <span>Style: {result.details.style.name}</span>}
            {(result.details?.width_cm || result.details?.height_cm) && (
              <span>{result.details.width_cm || "?"} x {result.details.height_cm || "?"} cm</span>
            )}
            {result.details?.price_per_sqm != null && <span>₹{result.details.price_per_sqm}/sqm</span>}
          </div>

          {/* Location */}
          <div className="bg-stone-50 rounded-lg px-3 py-2 mt-2 text-sm">
            <p className="text-stone-500 text-xs mb-0.5">
              📍 Warehouse Location
            </p>
            {result.location?.aisle ? (
              <p className="font-medium text-stone-700 text-xs">
                {result.location.display ||
                  `${result.location.warehouse || "Warehouse"} | Aisle ${result.location.aisle} -> Rack ${result.location.rack} -> Bin ${result.location.bin}`}
              </p>
            ) : (
              <p className="text-stone-500 italic text-xs">
                {result.location?.display || `${result.location?.warehouse || "Warehouse"} | Location pending assignment`}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Stock Row */}
      <div className="flex items-center justify-between text-sm mt-3
                      pt-3 border-t border-stone-100">
        <span className="text-stone-500">📦 Inventory</span>
        <span
          className={`font-semibold ${
            result.stock.is_low ? "text-red-500" : "text-green-600"
          }`}
        >
          {result.stock.quantity == null ? "Information unavailable" : `${result.stock.quantity} ${result.stock.unit}`}
          {result.stock.is_low && " ⚠️ Low"}
        </span>
      </div>

      <a
        href={`/dashboard/tiles/${result.tile_id}`}
        className="mt-4 inline-flex text-sm font-semibold text-cyan-700 hover:text-cyan-900"
      >
        View product details →
      </a>
    </div>
  );
}