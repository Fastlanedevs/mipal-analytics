"use client";

import { useGetProductionQueueQuery } from "@/store/services/dashboardApi";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { PageHeader } from "@/components/common/PageHeader";
import { Clipboard, AlertCircle, AlertTriangle, Mail } from "lucide-react";
import { mockProductionQueue } from "@/mocks/productionQueueData";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
  AreaChart,
  Area,
} from "recharts";
import {
  Box,
  CircleDollarSign,
  Timer,
  TrendingUp,
  Users,
  DollarSign,
} from "lucide-react";
import { ProductionQueueItem } from "@/store/services/dashboardApi";
import { MapPin } from "lucide-react";
import ProductionQueueMap from "@/components/maps/ProductionQueueMap";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import { LEMCAL_URL } from "@/constants";
import { useTranslations } from "next-intl";

interface StatCardProps {
  icon: React.ReactNode;
  title: string;
  description: string;
  value: number;
  valueClassName?: string;
}

interface DemoCardProps {
  children: React.ReactNode;
  tooltipContent?: string;
  className?: string;
  showOverlay?: boolean;
}

const BlurOverlay = () => (
  <div className="absolute inset-0 bg-background/30 backdrop-blur-sm z-20 rounded-lg pointer-events-none" />
);

const PremiumFeatureMessage = () => {
  const t = useTranslations("productionDashboard");
  return (
    <div className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-50">
      <div className="relative z-50 ">
        <div className="text-center space-y-4">
          <p className="text-muted-foreground">
            {t("productionDashboardIsInEnterprisePlan")}
          </p>
          <Button
            variant="default"
            size="lg"
            className="gap-2"
            onClick={() => window.open(LEMCAL_URL, "_blank")}
          >
            <Mail className="h-4 w-4" />
            {t("contactUs")}
          </Button>
        </div>
      </div>
    </div>
  );
};

const DemoCard = ({
  children,
  tooltipContent,
  className,
  showOverlay = false,
}: DemoCardProps) => (
  <Card className={`group relative overflow-hidden ${className}`}>
    {showOverlay && <BlurOverlay />}
    {children}
  </Card>
);

const StatCard = ({
  icon,
  title,
  description,
  value,
  valueClassName,
}: StatCardProps) => (
  <DemoCard
    tooltipContent="Demo analytics"
    className="flex flex-row justify-between shadow-none cursor-help"
    showOverlay={false}
  >
    <CardHeader className="pb-2">
      <CardTitle className="text-sm font-medium flex items-center gap-2">
        {icon}
        {title}
      </CardTitle>
      <CardDescription>{description}</CardDescription>
    </CardHeader>
    <CardContent className="p-6">
      <div className={`text-3xl font-bold ${valueClassName ?? ""}`}>
        {value}
      </div>
    </CardContent>
  </DemoCard>
);

const getStageData = (data: ProductionQueueItem[] | undefined) => {
  if (!data) {
    return [];
  }
  return Object.entries(
    data.reduce(
      (acc, item) => {
        acc[item.stage] = (acc[item.stage] || 0) + 1;
        return acc;
      },
      {} as Record<string, number>
    )
  ).map(([name, value]) => ({ name, value }));
};

const getPriorityDistribution = (data: ProductionQueueItem[] | undefined) => {
  if (!data) {
    return [];
  }
  return Object.entries(
    data.reduce(
      (acc, item) => {
        acc[item.priority] = (acc[item.priority] || 0) + 1;
        return acc;
      },
      {} as Record<string, number>
    )
  ).map(([name, value]) => ({ name, value }));
};

const getDeliveryTimeline = (data: ProductionQueueItem[] | undefined) => {
  if (!data) {
    return [];
  }
  return data
    .map((item) => ({
      orderId: item.order_id,
      progress: item.progress,
      startDate: new Date(item.start_date).getTime(),
      deliveryDate: new Date(item.delivery_date).getTime(),
    }))
    .sort((a, b) => a.startDate - b.startDate);
};

const COLORS = ["#0088FE", "#00C49F", "#FFBB28", "#FF8042", "#8884d8"];

const getVolumeData = (data: ProductionQueueItem[] | undefined) => {
  if (!data) {
    return [];
  }
  // Group by date and sum quantities
  const volumeByDate = data.reduce(
    (acc, item) => {
      const date = new Date(item.start_date).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
      });
      acc[date] = (acc[date] || 0) + item.quantity;
      return acc;
    },
    {} as Record<string, number>
  );

  return Object.entries(volumeByDate)
    .map(([date, volume]) => ({ date, volume }))
    .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
};

const getCustomerData = (data: ProductionQueueItem[] | undefined) => {
  if (!data) {
    return [];
  }
  // Group by date and count unique customers
  const customersByDate = data.reduce(
    (acc, item) => {
      const date = new Date(item.start_date).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
      });
      if (!acc[date]) {
        acc[date] = new Set();
      }
      acc[date].add(item.customer);
      return acc;
    },
    {} as Record<string, Set<string>>
  );

  return Object.entries(customersByDate)
    .map(([date, customers]) => ({ date, customers: customers.size }))
    .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
};

const getRevenueData = (data: ProductionQueueItem[] | undefined) => {
  if (!data) {
    return [];
  }
  // Simulate revenue based on quantity (assuming average price per unit)
  const AVERAGE_PRICE = 100; // Simulated price per unit
  const revenueByDate = data.reduce(
    (acc, item) => {
      const date = new Date(item.start_date).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
      });
      acc[date] = (acc[date] || 0) + item.quantity * AVERAGE_PRICE;
      return acc;
    },
    {} as Record<string, number>
  );

  return Object.entries(revenueByDate)
    .map(([date, amount]) => ({ date, amount }))
    .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
};

const calculateMetrics = (data: ProductionQueueItem[] | undefined) => {
  if (!data) {
    return {
      totalOrders: 0,
      totalQuantity: 0,
      avgProgress: 0,
      failedQC: 0,
      qcPassRate: 0,
    };
  }

  const totalOrders = data.length;
  const totalQuantity = data.reduce((sum, item) => sum + item.quantity, 0);
  const avgProgress =
    data.reduce((sum, item) => sum + item.progress, 0) / totalOrders;
  const failedQC = data.filter((item) => item.status === "Failed").length;

  return {
    totalOrders,
    totalQuantity,
    avgProgress,
    failedQC,
    qcPassRate: ((totalOrders - failedQC) / totalOrders) * 100,
  };
};

export default function ProductionDashboard() {
  const { data: queueData, isLoading } = useGetProductionQueueQuery();
  const { toast } = useToast();
  const t = useTranslations("productionDashboard");
  const [isGeocodingLoading, setIsGeocodingLoading] = useState(false);

  // Use mock data if API data is not available
  const displayData =
    queueData && queueData?.length > 0 ? queueData : mockProductionQueue;

  const getPriorityBadgeVariant = (priority: string) => {
    switch (priority.toLowerCase()) {
      case "high":
        return "destructive";
      case "medium":
        return "secondary";
      default:
        return "default";
    }
  };

  const getQCStatusBadgeVariant = (status: string) => {
    switch (status.toLowerCase()) {
      case "passed":
        return "default";
      case "failed":
        return "destructive";
      default:
        return "secondary";
    }
  };

  const handleContactClick = () => {
    window.open(LEMCAL_URL, "_blank");
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      <PageHeader
        title={t("businessOverview")}
        description={t("monitorYourKeyBusinessMetrics")}
        actions={
          <div className="flex flex-row gap-2">
            <p className="pt-1">{t("productionDashboardIsInEnterprisePlan")}</p>
            <Button
              variant="outline"
              size="sm"
              className="gap-2"
              onClick={handleContactClick}
            >
              <Mail className="h-4 w-4" />
              {t("contactUs")}
            </Button>
          </div>
        }
      />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard
          icon={<Clipboard className="h-4 w-4" />}
          title={t("totalOrders")}
          description={t("totalOrdersInQueue")}
          value={displayData?.length ?? 0}
        />
        <StatCard
          icon={<AlertCircle className="h-4 w-4" />}
          title={t("highPriority")}
          description={t("urgentAttentionNeeded")}
          value={
            displayData?.filter((item) => item.priority === "High").length ?? 0
          }
          valueClassName="text-destructive"
        />
        <StatCard
          icon={<AlertTriangle className="h-4 w-4" />}
          title={t("qcIssues")}
          description={t("failedQualityChecks")}
          value={
            displayData?.filter((item) => item.status === "Failed").length ?? 0
          }
          valueClassName="text-warning"
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard
          icon={<AlertTriangle className="h-4 w-4" />}
          title={t("qcPassRate")}
          description={t("qualityControlSuccess")}
          value={Math.round(
            (displayData?.filter((item) => item.status === "Passed").length ??
              0 / (displayData?.length ?? 0)) * 100
          )}
          valueClassName={
            (displayData?.filter((item) => item.status === "Passed").length ??
              0 / (displayData?.length ?? 0)) *
              100 >
            90
              ? "text-success"
              : "text-warning"
          }
        />
        <StatCard
          icon={<Box className="h-4 w-4" />}
          title={t("averageOrderSize")}
          description={t("unitsPerOrder")}
          value={Math.round(
            (displayData?.reduce((sum, item) => sum + item.quantity, 0) ?? 0) /
              (displayData?.length ?? 0)
          )}
        />
        <StatCard
          icon={<Timer className="h-4 w-4" />}
          title={t("onTimeDelivery")}
          description={t("ordersWithinSchedule")}
          value={Math.round(
            (displayData?.filter(
              (item) =>
                new Date(item.delivery_date).getTime() >= new Date().getTime()
            ).length ?? 0) / (displayData?.length ?? 0)
          )}
          valueClassName="text-success"
        />
      </div>

      <PremiumFeatureMessage />

      {/* Production Queue Table */}
      <DemoCard
        tooltipContent="Demo analytics"
        className="overflow-hidden"
        showOverlay={true}
      >
        <CardContent className="p-0">
          <div className="max-h-[500px] overflow-y-auto relative">
            <Table>
              <TableHeader className="bg-muted/95 backdrop-blur supports-[backdrop-filter]:bg-muted/60 dark:bg-foreground/5 sticky top-0 z-10">
                <TableRow>
                  <TableHead>OrderID</TableHead>
                  <TableHead>Customer</TableHead>
                  <TableHead>Wood Type</TableHead>
                  <TableHead>Rubber Type</TableHead>
                  <TableHead>Quantity</TableHead>
                  <TableHead>Priority</TableHead>
                  <TableHead>Stage</TableHead>
                  <TableHead>Progress</TableHead>
                  <TableHead>QC Status</TableHead>
                  <TableHead>Start Date</TableHead>
                  <TableHead>Delivery Date</TableHead>
                  <TableHead>Issues</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {displayData?.map((item) => (
                  <TableRow key={item.order_id}>
                    <TableCell className="font-medium">
                      {item.order_id}
                    </TableCell>
                    <TableCell>{item.customer}</TableCell>
                    <TableCell>{item.wood_type}</TableCell>
                    <TableCell>{item.rubber_type}</TableCell>
                    <TableCell>{item.quantity}</TableCell>
                    <TableCell>
                      <Badge variant={getPriorityBadgeVariant(item.priority)}>
                        {item.priority}
                      </Badge>
                    </TableCell>
                    <TableCell>{item.stage}</TableCell>
                    <TableCell>
                      <div className="space-y-1">
                        <Progress value={item.progress} />
                        <p className="text-xs text-muted-foreground">
                          {item.progress}%
                        </p>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant={getQCStatusBadgeVariant(item.status)}>
                        {item.status}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {new Date(item.start_date).toLocaleDateString()}
                    </TableCell>
                    <TableCell>
                      {new Date(item.delivery_date).toLocaleDateString()}
                    </TableCell>
                    <TableCell>
                      {item.issues ? (
                        <span className="text-destructive">{item.issues}</span>
                      ) : (
                        <span className="text-muted-foreground">-</span>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </DemoCard>

      {/* Production Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {/* Total Production Volume */}
        <DemoCard
          tooltipContent="Demo analytics"
          className="flex-1 min-w-[300px] cursor-help"
          showOverlay={true}
        >
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Box className="h-4 w-4" />
              {t("productionVolume")}
            </CardTitle>
            <CardDescription>{t("totalUnitsInProduction")}</CardDescription>
          </CardHeader>
          <CardContent className="p-6">
            <div className="text-3xl font-bold">
              {calculateMetrics(displayData).totalQuantity.toLocaleString()}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {t("unitsInQueue")}
            </p>
          </CardContent>
        </DemoCard>

        {/* Average Progress */}
        <DemoCard
          tooltipContent="Demo analytics"
          className="flex-1 min-w-[300px] cursor-help"
          showOverlay={true}
        >
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Timer className="h-4 w-4" />
              {t("averageProgress")}
            </CardTitle>
            <CardDescription>{t("overallCompletionRate")}</CardDescription>
          </CardHeader>
          <CardContent className="p-6">
            <div className="text-3xl font-bold">
              {calculateMetrics(displayData).avgProgress.toFixed(1)}%
            </div>
            <Progress
              value={calculateMetrics(displayData).avgProgress}
              className="mt-2"
            />
          </CardContent>
        </DemoCard>

        {/* QC Pass Rate */}
        <DemoCard
          tooltipContent="Demo analytics"
          className="flex-1 min-w-[300px] cursor-help"
          showOverlay={true}
        >
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <CircleDollarSign className="h-4 w-4" />
              {t("qualityControl")}
            </CardTitle>
            <CardDescription>{t("passRateForQcChecks")}</CardDescription>
          </CardHeader>
          <CardContent className="p-6">
            <div className="text-3xl font-bold">
              {calculateMetrics(displayData).qcPassRate.toFixed(1)}%
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {t("passRate")}
            </p>
          </CardContent>
        </DemoCard>

        {/* Order Value */}
        <DemoCard
          tooltipContent="Demo analytics"
          className="flex-1 min-w-[300px] cursor-help"
          showOverlay={true}
        >
          <CardHeader>
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <TrendingUp className="h-4 w-4" />
              {t("orderTrend")}
            </CardTitle>
            <CardDescription>{t("weeklyOrderVolume")}</CardDescription>
          </CardHeader>
          <CardContent className="p-6">
            <div className="h-[50px]">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={getVolumeData(displayData)}>
                  <Area
                    type="monotone"
                    dataKey="volume"
                    stroke="#8884d8"
                    fill="#8884d8"
                    fillOpacity={0.3}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </DemoCard>
      </div>

      <div className="flex flex-wrap gap-6">
        {/* Gross Volume Chart */}
        <DemoCard
          tooltipContent="Demo analytics"
          className="flex-1 min-w-[300px] cursor-help"
          showOverlay={true}
        >
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <TrendingUp className="w-4 h-4" />
              {t("grossVolume")}
            </CardTitle>
            <CardDescription>{t("dailyProductionVolume")}</CardDescription>
          </CardHeader>
          <CardContent className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={getVolumeData(displayData)}>
                <defs>
                  <linearGradient id="colorVolume" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#8884d8" stopOpacity={0.8} />
                    <stop offset="95%" stopColor="#8884d8" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="date"
                  angle={-45}
                  textAnchor="end"
                  height={60}
                  interval={0}
                  style={{ fontSize: "12px" }}
                />
                <YAxis />
                <Tooltip />
                <Area
                  type="monotone"
                  dataKey="volume"
                  stroke="#8884d8"
                  fillOpacity={1}
                  fill="url(#colorVolume)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </DemoCard>

        {/* New Customers Chart */}
        <DemoCard
          tooltipContent="Demo analytics"
          className="flex-1 min-w-[300px] cursor-help"
          showOverlay={true}
        >
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Users className="w-4 h-4" />
              {t("customers")}
            </CardTitle>
            <CardDescription>{t("dailyCustomerDistribution")}</CardDescription>
          </CardHeader>
          <CardContent className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={getCustomerData(displayData)}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="date"
                  angle={-45}
                  textAnchor="end"
                  height={60}
                  interval={0}
                  style={{ fontSize: "12px" }}
                />
                <YAxis />
                <Tooltip />
                <Line
                  type="monotone"
                  dataKey="customers"
                  stroke="#82ca9d"
                  strokeWidth={2}
                />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </DemoCard>

        {/* Revenue Chart */}
        <DemoCard
          tooltipContent="Demo analytics"
          className="flex-1 min-w-[300px] cursor-help"
          showOverlay={true}
        >
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <DollarSign className="w-4 h-4" />
              {t("revenue")}
            </CardTitle>
            <CardDescription>{t("dailyRevenueOverview")}</CardDescription>
          </CardHeader>
          <CardContent className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={getRevenueData(displayData)}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="date"
                  angle={-45}
                  textAnchor="end"
                  height={60}
                  interval={0}
                  style={{ fontSize: "12px" }}
                />
                <YAxis />
                <Tooltip />
                <Bar dataKey="amount" fill="#0ea5e9" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </DemoCard>

        {/* Update the Map Card with proper sizing and loading state */}
        <DemoCard
          tooltipContent="Demo analytics"
          className="flex-1 min-w-[600px] cursor-help"
          showOverlay={true}
        >
          <div className="flex flex-row justify-between items-center p-6">
            <CardHeader className="p-0">
              <CardTitle className="text-lg flex items-center gap-2">
                <MapPin className="w-4 h-4" />
                {t("deliveryLocations")}
              </CardTitle>
              <CardDescription>
                {t("geographicDistributionOfOrders")}
              </CardDescription>
            </CardHeader>
            {(isLoading || isGeocodingLoading) && (
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
            )}
          </div>
          <CardContent className="p-0">
            <ProductionQueueMap
              data={displayData}
              setIsGeocodingLoading={setIsGeocodingLoading}
            />
          </CardContent>
        </DemoCard>

        {/* Production Stages Chart */}
        <DemoCard
          tooltipContent="Demo analytics"
          className="flex-1 min-w-[300px] cursor-help"
          showOverlay={true}
        >
          <CardHeader>
            <CardTitle className="text-lg">{t("productionStages")}</CardTitle>
            <CardDescription>
              {t("distributionOfOrdersByStage")}
            </CardDescription>
          </CardHeader>
          <CardContent className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={getStageData(displayData)}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="name"
                  angle={-35}
                  textAnchor="end"
                  height={80}
                  interval={0}
                  style={{ fontSize: "12px" }}
                />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="value" stroke="#8884d8" />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </DemoCard>
        {/* Priority Distribution Chart */}
        <DemoCard
          tooltipContent="Demo analytics"
          className="flex-1 min-w-[300px] cursor-help"
          showOverlay={true}
        >
          <CardHeader>
            <CardTitle className="text-lg">
              {t("priorityDistribution")}
            </CardTitle>
            <CardDescription>{t("ordersByPriorityLevel")}</CardDescription>
          </CardHeader>
          <CardContent className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={getPriorityDistribution(displayData)}
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  dataKey="value"
                  label
                >
                  {getPriorityDistribution(displayData).map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={COLORS[index % COLORS.length]}
                    />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </DemoCard>
        {/* Production Flow Visualization */}
        <DemoCard
          tooltipContent="Demo analytics"
          className="flex-1 min-w-[300px] cursor-help"
          showOverlay={true}
        >
          <CardHeader>
            <CardTitle className="text-lg">{t("productionTimeline")}</CardTitle>
            <CardDescription>
              {t("orderProgressAndDeliveryTimeline")}
            </CardDescription>
          </CardHeader>
          <CardContent className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={getDeliveryTimeline(displayData)}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="startDate"
                  tickFormatter={(value) =>
                    new Date(value).toLocaleDateString()
                  }
                />
                <YAxis dataKey="progress" />
                <Tooltip
                  labelFormatter={(value) =>
                    new Date(value).toLocaleDateString()
                  }
                />
                <Line type="monotone" dataKey="progress" stroke="#8884d8" />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </DemoCard>
      </div>
      <div className="flex-1 min-w-[300px]"></div>
    </div>
  );
}
