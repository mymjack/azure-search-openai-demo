import { Example } from "./Example";

import styles from "./Example.module.css";

export type ExampleModel = {
    text: string;
    value: string;
};

const EXAMPLES: ExampleModel[] = [
    { text: "What are the top 10 topics since 2023-01-01?", value: "What are the top 10 topics since 2023-01-01?" },
    { text: "What's the new topics in version 5.43.1?", value: "What's the new topics in version 5.43.1?" },
    {
        text: "What's the only topics in May 2023?",
        value: "What's the only topics in May 2023?"
    }
];

interface Props {
    onExampleClicked: (value: string) => void;
}

export const ExampleList = ({ onExampleClicked }: Props) => {
    return (
        <ul className={styles.examplesNavList}>
            {EXAMPLES.map((x, i) => (
                <li key={i}>
                    <Example text={x.text} value={x.value} onClick={onExampleClicked} />
                </li>
            ))}
        </ul>
    );
};
