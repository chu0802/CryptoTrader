import { init, registerIndicator } from 'https://cdn.skypack.dev/klinecharts'

async function fetchData() {
  return fetch('../results/grid_trading/profit_flow.json')
      .then(response => {
          if (!response.ok) {
              throw new Error('Network response was not ok');
          }
          return response.json(); // Parse the JSON response
      })
      .then(data => {
        const profits = data.map(entry => ({
            close: entry.profit,
            high: entry.price,
            low: 100 * entry.profit / 182,
            open: entry.profit,
            timestamp: new Date(entry.time).getTime()
        }));
        return profits;
      });
}

async function fetchPrice() {
  return fetch('../data/ondousdt/prices.json')
      .then(response => {
          if (!response.ok) {
              throw new Error('Network response was not ok');
          }
          return response.json(); // Parse the JSON response
      })
      .then(data => {
          const profits = Object.entries(data).map(([key, value]) => ({
              close: value.close,
              high: value.high,
              low: value.low,
              open: value.open,
              timestamp: new Date(key).getTime()
          }));
          return profits;
      });
}

const chart = init('k-line-chart')
chart.setStyles({
  candle: {
    type: 'area',
    tooltip: {
      showRule: 'follow_cross',
      showType: 'rect',
      custom: [
        { title: 'Time: ', value: '{time}'},
        { title: 'Profit: ', value: '{close}'},
        { title: 'Current Price: ', value: '{high}'},
        { title: 'ROI: ', value: '{low}%'},
        { title: '', value: ''},
        { title: '', value: ''}
      ],
      rect: {
        position: 'pointer',
        offsetLeft: 50,
        offsetTop: 20,
        offsetRight: 50,
        offsetBottom: 20,

      }
    }
  },
  indicator: {
    tooltip: {
      showRule: 'none'
    },
    lines: [
      {
        style: 'dashed',
        smooth: false,
        dashedValue: [8, 4],
        size: 1,
        color: '#FF4500'
      }
    ]
}})

Promise.all([fetchData()])
  .then(([profitList]) => {
    let clickTime = 0;
    registerIndicator({
      name: 'Custom',
      figures: [
        { key: 'emoji' , title: 'Zero Line: ', type: 'line'}
      ],
      calc: (kLineDataList) => {
        return kLineDataList.map(kLineData => ({ emoji: 0}))
      },
      draw: ({
        ctx,
        barSpace,
        visibleRange,
        indicator,
        xAxis,
        yAxis
      }) => {
        const { from, to } = visibleRange
        ctx.textAlign = 'center'

        const result = indicator.result
        for (let i = from; i < to; i++) {
          const data = result[i]
          const x = xAxis.convertToPixel(i)
          const y = yAxis.convertToPixel(data.emoji)
        }
        return false
      }
    })
    chart.applyNewData(profitList)
    chart.setPriceVolumePrecision(4, 4)

    const container = document.getElementById('container')
    const buttonContainer = document.createElement('div')
    buttonContainer.classList.add('button-container')
    const setbutton = document.createElement('button')
    setbutton.innerText = 'Set Zero Line'
    setbutton.addEventListener('click', function(){
      if (clickTime % 2 == 0){
        setbutton.innerText = 'Remove Zero Line'
        chart.createIndicator('Custom', true, {id: 'candle_pane'})
      }
      else {
        setbutton.innerText = 'Set Zero Line'
        chart.removeIndicator('candle_pane', 'Custom')
      }
      clickTime ++
    })

    const febbuttoon = document.createElement('button')
    febbuttoon.innerText = 'Draw Fib. Line'
    febbuttoon.addEventListener('click', () => { chart.createOverlay('rayLine') })

    buttonContainer.appendChild(setbutton)
    buttonContainer.appendChild(febbuttoon)
    container.appendChild(buttonContainer)

  })
