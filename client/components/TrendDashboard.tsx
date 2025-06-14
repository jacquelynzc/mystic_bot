import { useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";

export default function TrendDashboard() {
    const [trends, setTrends] = useState([]);

    useEffect(() => {
        fetch("http://localhost:3001/api/trends")
            .then((res) => res.json())
            .then((data) => setTrends(data));
    }, []);

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 p-4">
            {trends.map((trend) => (
                <Card key={trend.id} className="rounded-2xl shadow-md">
                    <CardContent>
                        <h2 className="text-xl font-semibold mb-2">{trend.name}</h2>
                        <p className="text-sm text-gray-500 mb-2">Score: {trend.score}</p>
                        <p className="text-sm text-gray-700">{trend.insight}</p>
                    </CardContent>
                </Card>
            ))}
        </div>
    );
}
