type KnownWordsOption = {
  value: number
  label: string
}

const knownWordsOptions: KnownWordsOption[] = [
  { value: 1000, label: 'COCA 1000' },
  { value: 1600, label: '初中' },
  { value: 2000, label: 'COCA 2000' },
  { value: 3000, label: 'COCA 3000' },
  { value: 3500, label: '高中' },
  { value: 4500, label: '四级' },
  { value: 5000, label: 'COCA 5000' },
  { value: 5500, label: '六级' },
  { value: 8000, label: 'COCA 8000' },
  { value: 10000, label: 'COCA 10000' },
  { value: 12000, label: 'COCA 12000' },
  { value: 15000, label: 'COCA 15000' }
]

export const useKnownWordsOptions = () => {
  const getKnownWordsLabel = (value: number | null | undefined) => {
    if (!value) {
      return '--'
    }

    const matched = knownWordsOptions.find((option) => option.value === value)
    return matched ? matched.label : `COCA ${value}`
  }

  return {
    knownWordsOptions,
    getKnownWordsLabel
  }
}
