import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function SalesPitchPlan() {
  return (
    <div className="min-h-screen p-4 bg-orange-50 sm:p-6 lg:p-8">
      <div className="flex flex-col items-center justify-between p-4 mb-6 space-y-4 text-white bg-orange-500 rounded-lg shadow-lg sm:flex-row sm:space-y-0">
        <h1 className="text-2xl font-bold sm:text-3xl">Sales Pitch Deck</h1>
        <div className="text-center sm:text-right">
          <p className="font-semibold">Our Company</p>
          <p>Strategy & Operations Team</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 bg-orange-400 rounded-full sm:w-8 sm:h-8"></div>
          <div className="w-6 h-6 bg-orange-300 rounded-full sm:w-8 sm:h-8"></div>
          <Avatar className="w-6 h-6 sm:w-8 sm:h-8">
            <AvatarFallback>[IN]</AvatarFallback>
          </Avatar>
          <Avatar className="w-6 h-6 sm:w-8 sm:h-8">
            <AvatarFallback>[IN]</AvatarFallback>
          </Avatar>
          <Avatar className="w-6 h-6 sm:w-8 sm:h-8">
            <AvatarFallback>[IN]</AvatarFallback>
          </Avatar>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
        <Card className="transition-shadow duration-300 bg-orange-100 shadow-md hover:shadow-lg">
          <CardHeader className="bg-orange-200 rounded-t-lg">
            <CardTitle className="text-lg font-bold text-orange-800 sm:text-xl">
              Company Overview
            </CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-1 gap-4 p-4 sm:grid-cols-2">
            <InfoCard
              title="Areas of Work"
              content="Audit & Assurance, Consulting, Financial Advisory, Risk Advisory, Legal, Tax"
            />
            <InfoCard
              title="Areas of Operation"
              content="Global, United States, United Kingdom, Canada, Australia, Germany, France, Japan, China, India, Brazil"
            />
          </CardContent>
        </Card>

        <Card className="transition-shadow duration-300 bg-orange-100 shadow-md hover:shadow-lg">
          <CardHeader className="bg-orange-200 rounded-t-lg">
            <CardTitle className="text-lg font-bold text-orange-800 sm:text-xl">
              Market Analysis
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 space-y-4">
            <Card className="bg-white">
              <CardHeader>
                <CardTitle className="text-sm font-bold text-orange-600">
                  Global Market Trends
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="w-full h-24 p-2 text-sm rounded bg-orange-50">
                  Audit & Assurance services are experiencing heightened demand
                  due to increased regulatory requirements and the globalization
                  of businesses. The current global market valuation is in the
                  range of billions with projected steady growth.
                </div>
              </CardContent>
            </Card>
            <InfoCard
              title="Competitive Landscape"
              content="Key competitors include PwC, EY, KPMG, and Deloitte. Our AI integration offers a competitive edge."
            />
          </CardContent>
        </Card>

        <Card className="transition-shadow duration-300 bg-orange-100 shadow-md hover:shadow-lg">
          <CardHeader className="bg-orange-200 rounded-t-lg">
            <CardTitle className="text-lg font-bold text-orange-800 sm:text-xl">
              Product/Service Offering
            </CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-1 gap-4 p-4 sm:grid-cols-2">
            <InfoCard
              title="Audit & Assurance"
              content="Robust services that help businesses remain compliant and efficient."
            />
            <InfoCard
              title="Features"
              content="Regulatory Compliance, Risk Management, Technological Integration"
            />
          </CardContent>
        </Card>

        <Card className="transition-shadow duration-300 bg-orange-100 shadow-md hover:shadow-lg">
          <CardHeader className="bg-orange-200 rounded-t-lg">
            <CardTitle className="text-lg font-bold text-orange-800 sm:text-xl">
              Sales Strategy
            </CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-3 gap-2 text-sm">
            <div className="font-bold text-orange-700">2023 Performance</div>
            <div className="font-bold text-orange-700">2024 Projections</div>
            <div className="font-bold text-orange-700">Team Resources</div>
            <div>Q1: $4.2B</div>
            <div>Q1: $4.8B</div>
            <div>Team Size: 4 People</div>
            <div>Q2: $4.5B</div>
            <div>Q2: $5.0B</div>
            <div>Equip the team with additional resources.</div>
            <div>Q3: $4.3B</div>
            <div></div>
            <div>Leverage AI innovations.</div>
            <div>Q4: $4.7B</div>
          </CardContent>
        </Card>

        <Card className="transition-shadow duration-300 bg-orange-100 shadow-md hover:shadow-lg">
          <CardHeader className="bg-orange-200 rounded-t-lg">
            <CardTitle className="text-lg font-bold text-orange-800 sm:text-xl">
              Goals & Objectives
            </CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-4 p-4 md:grid-cols-4">
            <ResourceItem>Increase Revenue Growth</ResourceItem>
            <ResourceItem>Expand Audit & Assurance globally</ResourceItem>
            <ResourceItem>Value-Based Revenue</ResourceItem>
            <ResourceItem>Emphasize premier services</ResourceItem>
          </CardContent>
        </Card>

        <Card className="transition-shadow duration-300 bg-orange-100 shadow-md hover:shadow-lg">
          <CardHeader className="bg-orange-200 rounded-t-lg">
            <CardTitle className="text-lg font-bold text-orange-800 sm:text-xl">
              Conclusion
            </CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-1 gap-4 p-4 sm:grid-cols-2">
            <InfoCard
              title="Summary"
              content="Integrated services and innovative approaches position us strongly in the market."
            />
            <InfoCard
              title="Key Takeaways"
              content="Expansion of Audit & Assurance, Global Reach, Competitive Advantage with AI Integration, Proven track record and projected growth."
            />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function InfoCard({ title, content }: { title: string; content: string }) {
  return (
    <Card className="transition-shadow duration-300 bg-white shadow hover:shadow-md">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-bold text-orange-600">
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent className="text-sm">{content}</CardContent>
    </Card>
  );
}

function ResourceItem({ children }: { children: React.ReactNode }) {
  return (
    <div className="p-2 text-sm text-center transition-colors duration-300 bg-white rounded shadow hover:bg-orange-50">
      {children}
    </div>
  );
}
