//+------------------------------------------------------------------+
//|                                                 TrendGuardEA.mq4 |
//|  Trend-following EA with strict risk management.                 |
//|  Entry : fast/slow EMA cross, filtered by a long trend EMA + RSI |
//|  Exit  : ATR-based stop loss / take profit, break-even, trailing |
//|  Risk  : fixed % of equity per trade, daily loss limit,          |
//|          spread filter, trading-hours filter, 1 trade per symbol |
//|                                                                  |
//|  NO STRATEGY GUARANTEES PROFITS. Backtest and run on a demo      |
//|  account before risking real money.                              |
//+------------------------------------------------------------------+
#property copyright "TrendGuardEA"
#property version   "1.00"
#property strict

//--- Strategy
input int    FastEMA            = 20;     // Fast EMA period
input int    SlowEMA            = 50;     // Slow EMA period
input int    TrendEMA           = 200;    // Trend filter EMA period
input int    RSIPeriod          = 14;     // RSI period
input double RSIBuyMin          = 50.0;   // Buy only if RSI above
input double RSIBuyMax          = 70.0;   // ...and below (avoid overbought)
input double RSISellMax         = 50.0;   // Sell only if RSI below
input double RSISellMin         = 30.0;   // ...and above (avoid oversold)

//--- Exits
input int    ATRPeriod          = 14;     // ATR period
input double SL_ATR_Mult        = 1.5;    // Stop loss = ATR * mult
input double TP_ATR_Mult        = 3.0;    // Take profit = ATR * mult
input bool   UseBreakEven       = true;   // Move SL to entry after BE_ATR_Mult*ATR
input double BE_ATR_Mult        = 1.0;
input bool   UseTrailing        = true;   // ATR trailing stop
input double Trail_ATR_Mult     = 1.5;

//--- Risk management
input double RiskPercent        = 1.0;    // % of equity risked per trade
input double MaxDailyLossPct    = 3.0;    // Stop trading for the day after this loss %
input int    MaxSpreadPoints    = 30;     // Skip entries when spread is wider (points)
input int    StartHour          = 8;      // Trading window start (server time)
input int    EndHour            = 20;     // Trading window end (server time)
input int    MagicNumber        = 240117;
input int    Slippage           = 3;

datetime lastBarTime = 0;
double   dayStartEquity = 0;
int      currentDay = -1;

//+------------------------------------------------------------------+
int OnInit()
{
   if(FastEMA >= SlowEMA)        { Print("FastEMA must be < SlowEMA"); return INIT_PARAMETERS_INCORRECT; }
   if(RiskPercent <= 0 || RiskPercent > 5) { Print("RiskPercent must be in (0,5]"); return INIT_PARAMETERS_INCORRECT; }
   if(SL_ATR_Mult <= 0 || TP_ATR_Mult <= 0) return INIT_PARAMETERS_INCORRECT;
   dayStartEquity = AccountEquity();
   currentDay = TimeDay(TimeCurrent());
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnTick()
{
   UpdateDailyEquity();
   ManageOpenTrade();

   // Evaluate entries only once per closed bar
   if(Time[0] == lastBarTime) return;
   lastBarTime = Time[0];

   if(Bars < TrendEMA + 5)          return;
   if(HasOpenTrade())               return;
   if(DailyLossLimitHit())          return;
   if(!InTradingHours())            return;
   if(SpreadPoints() > MaxSpreadPoints) return;

   int signal = GetSignal();
   if(signal != 0) OpenTrade(signal);
}

//+------------------------------------------------------------------+
//| +1 buy, -1 sell, 0 none. Uses closed bars (shift 1 and 2).       |
//+------------------------------------------------------------------+
int GetSignal()
{
   double fast1  = iMA(NULL, 0, FastEMA,  0, MODE_EMA, PRICE_CLOSE, 1);
   double fast2  = iMA(NULL, 0, FastEMA,  0, MODE_EMA, PRICE_CLOSE, 2);
   double slow1  = iMA(NULL, 0, SlowEMA,  0, MODE_EMA, PRICE_CLOSE, 1);
   double slow2  = iMA(NULL, 0, SlowEMA,  0, MODE_EMA, PRICE_CLOSE, 2);
   double trend  = iMA(NULL, 0, TrendEMA, 0, MODE_EMA, PRICE_CLOSE, 1);
   double rsi    = iRSI(NULL, 0, RSIPeriod, PRICE_CLOSE, 1);
   double close1 = Close[1];

   bool crossUp   = fast2 <= slow2 && fast1 > slow1;
   bool crossDown = fast2 >= slow2 && fast1 < slow1;

   if(crossUp   && close1 > trend && rsi > RSIBuyMin  && rsi < RSIBuyMax)  return  1;
   if(crossDown && close1 < trend && rsi < RSISellMax && rsi > RSISellMin) return -1;
   return 0;
}

//+------------------------------------------------------------------+
void OpenTrade(int dir)
{
   double atr = iATR(NULL, 0, ATRPeriod, 1);
   if(atr <= 0) return;

   double slDist = atr * SL_ATR_Mult;
   double tpDist = atr * TP_ATR_Mult;
   double minDist = MarketInfo(Symbol(), MODE_STOPLEVEL) * Point;
   if(slDist < minDist) slDist = minDist;
   if(tpDist < minDist) tpDist = minDist;

   double lots = CalcLots(slDist);
   if(lots <= 0) { Print("Lot size too small for current risk settings"); return; }

   RefreshRates();
   double price, sl, tp; int type;
   if(dir > 0) { type = OP_BUY;  price = Ask; sl = price - slDist; tp = price + tpDist; }
   else        { type = OP_SELL; price = Bid; sl = price + slDist; tp = price - tpDist; }

   int ticket = OrderSend(Symbol(), type, lots, NormalizeDouble(price, Digits), Slippage,
                          NormalizeDouble(sl, Digits), NormalizeDouble(tp, Digits),
                          "TrendGuardEA", MagicNumber, 0, dir > 0 ? clrDodgerBlue : clrTomato);
   if(ticket < 0) Print("OrderSend failed, error ", GetLastError());
}

//+------------------------------------------------------------------+
//| Lot size so that hitting the SL loses RiskPercent of equity.     |
//+------------------------------------------------------------------+
double CalcLots(double slDist)
{
   double riskMoney = AccountEquity() * RiskPercent / 100.0;
   double tickValue = MarketInfo(Symbol(), MODE_TICKVALUE);
   double tickSize  = MarketInfo(Symbol(), MODE_TICKSIZE);
   if(tickValue <= 0 || tickSize <= 0) return 0;

   double lossPerLot = slDist / tickSize * tickValue;
   if(lossPerLot <= 0) return 0;

   double lots    = riskMoney / lossPerLot;
   double step    = MarketInfo(Symbol(), MODE_LOTSTEP);
   double minLot  = MarketInfo(Symbol(), MODE_MINLOT);
   double maxLot  = MarketInfo(Symbol(), MODE_MAXLOT);

   lots = MathFloor(lots / step) * step;
   if(lots < minLot) return 0;          // never round UP past the risk budget
   if(lots > maxLot) lots = maxLot;
   return NormalizeDouble(lots, 2);
}

//+------------------------------------------------------------------+
void ManageOpenTrade()
{
   double atr = iATR(NULL, 0, ATRPeriod, 1);
   if(atr <= 0) return;

   for(int i = OrdersTotal() - 1; i >= 0; i--)
   {
      if(!OrderSelect(i, SELECT_BY_POS, MODE_TRADES)) continue;
      if(OrderSymbol() != Symbol() || OrderMagicNumber() != MagicNumber) continue;

      double open = OrderOpenPrice(), sl = OrderStopLoss(), newSL = sl;

      if(OrderType() == OP_BUY)
      {
         if(UseBreakEven && Bid - open >= atr * BE_ATR_Mult && sl < open) newSL = open;
         if(UseTrailing)
         {
            double t = Bid - atr * Trail_ATR_Mult;
            if(t > newSL && t > open) newSL = t;
         }
         if(newSL > sl + Point) ModifySL(newSL);
      }
      else if(OrderType() == OP_SELL)
      {
         if(UseBreakEven && open - Ask >= atr * BE_ATR_Mult && (sl > open || sl == 0)) newSL = open;
         if(UseTrailing)
         {
            double t = Ask + atr * Trail_ATR_Mult;
            if((t < newSL || newSL == 0) && t < open) newSL = t;
         }
         if(sl == 0 || newSL < sl - Point) ModifySL(newSL);
      }
   }
}

void ModifySL(double newSL)
{
   double minDist = MarketInfo(Symbol(), MODE_STOPLEVEL) * Point;
   if(OrderType() == OP_BUY  && Bid - newSL < minDist) return;
   if(OrderType() == OP_SELL && newSL - Ask < minDist) return;
   if(!OrderModify(OrderTicket(), OrderOpenPrice(), NormalizeDouble(newSL, Digits),
                   OrderTakeProfit(), 0, clrYellow))
      Print("OrderModify failed, error ", GetLastError());
}

//+------------------------------------------------------------------+
bool HasOpenTrade()
{
   for(int i = OrdersTotal() - 1; i >= 0; i--)
      if(OrderSelect(i, SELECT_BY_POS, MODE_TRADES) &&
         OrderSymbol() == Symbol() && OrderMagicNumber() == MagicNumber)
         return true;
   return false;
}

void UpdateDailyEquity()
{
   int d = TimeDay(TimeCurrent());
   if(d != currentDay) { currentDay = d; dayStartEquity = AccountEquity(); }
}

bool DailyLossLimitHit()
{
   if(dayStartEquity <= 0) return false;
   double lossPct = (dayStartEquity - AccountEquity()) / dayStartEquity * 100.0;
   return lossPct >= MaxDailyLossPct;
}

bool InTradingHours()
{
   int h = TimeHour(TimeCurrent());
   if(StartHour <= EndHour) return h >= StartHour && h < EndHour;
   return h >= StartHour || h < EndHour;   // window crossing midnight
}

double SpreadPoints() { return MarketInfo(Symbol(), MODE_SPREAD); }
//+------------------------------------------------------------------+
